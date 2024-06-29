#define __STDC_FORMAT_MACROS 1

#include <CLI/CLI.hpp>
#include <cassert>
#include <inttypes.h>
#include <iostream>
#include <fstream>
#include <common/Socket.h>
#include <common/Timer.h>
#include <stdio.h>
#include <thread>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <ctime>


using namespace std;

struct {
  int UDPPort{4003};
  int DataSize{9000};
  int SocketBufferSize{2000000};
} Settings;


//Helper class to enable file output in separate thread from packet receiver
class fileWriter{
public:

  //overloading the () operator makes this a callable function object (for multithreading)
  void operator()(const string& path, const vector<char> &data, int packets) {

    static const int BUFFERSIZE{4128};
    long long tWrite; //hopefully not that long ;)
    ofstream fileout; //declare output file stream

    //open binary file stream
    fileout.open(path, ios::out | ios::binary);

    //write data to file
    if (fileout.is_open()){

      //start timer for write operation
      auto tStart = std::chrono::high_resolution_clock::now();

      //write specified number of packets from data buffer
      fileout.write((char*)&data[0], packets*BUFFERSIZE);

      //stop timer and print write time to screen
      auto tEnd = std::chrono::high_resolution_clock::now();
      tWrite=std::chrono::duration_cast<std::chrono::milliseconds>(tEnd-tStart).count();
      printf("%i packets written, %i bytes each", packets, BUFFERSIZE);
      printf("%i bytes written in %llu ms\n", BUFFERSIZE*packets, tWrite);

      //close output file
      fileout.close();
    }
  }
};


CLI::App app{"UDP receiver with 32 bit sequence number check."};

int main(int argc, char *argv[3]) {
  //app.add_option("-a, --acquisitions", Settings.Acquisitions, "Acquisitions");
  //app.add_option("-ms, --milliseconds", Settings.Milliseconds, "Milliseconds");
  //CLI11_PARSE(app, argc, argv);
  char *nPtr = NULL;

  cout << "argc: " << argc << " argv: " << argv<< "\n"; 

  int intervals = strtol(argv[1], &nPtr, 10); //number of intervals to run for/files to write
  int intervalUs = 1000*strtol(argv[2], &nPtr, 10); //interval/output file time span in microseconds

  // printf("interval in microseconds: %i\n", intervalUs);

  int outputs = 0; //index variable for # of output files written

  const int B1M = 1000000;               //bytes per MB
  static const int BUFFERSIZE{4128};     //size of the packet buffer, in bytes
  char buffer[BUFFERSIZE];               //buffer is declared as chars b/c they're 1 byte each

  uint64_t RxBytesTotal{0};              //total bytes received since start of run time
  uint64_t RxBytes{0};                   //bytes recieved in last interval
  uint64_t RxTotPackets{0};              //total pakets received since start of run time
  uint64_t RxPackets{0};                 //packets received in last interval

  auto t = std::time(nullptr);           //time object for output file naming
  auto tm = *std::localtime(&t);         //system time object for output file naming
  std::ostringstream outFileStream;      //string for building output file name

  std::vector<char> sdb_datablock(700000000); //the large buffer for holding packets
  vector<char>::iterator sdb_iter = sdb_datablock.begin(); //iterator for navigating buffer vector

  std::vector<char> sdc_datablock(700000000); //the large buffer for holding packets
  vector<char>::iterator sdc_iter = sdc_datablock.begin(); //iterator for navigating buffer vector

  std::vector<char> sdd_datablock(700000000); //the large buffer for holding packets
  vector<char>::iterator sdd_iter = sdd_datablock.begin(); //iterator for navigating buffer vector

  // printf("memory blocks declared \n");

  //Set up socket and receiver to listen on it
  Socket::Endpoint local("10.66.192.33", 4003);
  UDPReceiver Receive(local);
  Receive.setBufferSizes(Settings.SocketBufferSize, Settings.SocketBufferSize);
  Receive.printBufferSizes();

  Timer UpdateTimer;   //timer for periodic console output on rx data rate
  auto USecs = UpdateTimer.timeus();

  Timer ExecTimer;  //timer for total execution time
  ExecTimer.now(); //start timer at beginning of execution
  auto ExecUSecs = ExecTimer.timeus(); //total time in microseconds

  // printf("Implimenting changes drew. 03282022\n");
  // printf("filling 1st buffer\n");
  int ReadSize = Receive.receive(buffer, BUFFERSIZE);
  // printf("data acquired, %i bytes received \n", ReadSize);

  // printf("entering receiver loop \n");

  //Run receiver for a pre-set number of 1000 ms intervals
  while(outputs < intervals) {

    UpdateTimer.now();
    USecs = UpdateTimer.timeus();

    while(USecs < intervalUs){
      //pull individual packet off the network interface
      int ReadSize = Receive.receive(buffer, BUFFERSIZE);

      if (ReadSize > 0) {
        //copy bytes from the buffer to the memmory position indicated by iter
        std::copy (buffer, buffer+BUFFERSIZE, sdb_iter);
        sdb_iter += BUFFERSIZE;  //advance the iterator to prep for buffering the next packet

        //increment counters for performance monitoring
        RxBytes += ReadSize;
        RxPackets++;
      }

      //update timer every 100 packets (~20k packets/sec => 100 packets = 5 ms
      if ((RxPackets % 100) == 0) USecs = UpdateTimer.timeus();

    } //end of while(USecs < intervalUs)

    //add bytes & packets recieved to totals
    RxTotPackets += RxPackets;
    RxBytesTotal += RxBytes;

    // //Output some performance stats to screen
    // printf("%" PRIu64 " Packets received, Total packets: %" PRIu64 "\n", RxPackets, RxTotPackets);
    // printf("Rx rate: %.2f Mbps, rx %" PRIu64 " MB (total: %" PRIu64 " MB) %" PRIu64 " usecs \n",
    //        RxBytes * 8.0 / (USecs / 1000000.0) / B1M, RxBytes / B1M, RxBytesTotal / B1M, USecs);
    // ExecUSecs = ExecTimer.timeus();
    // printf("Total execution time =  %" PRIu64 " usecs \n", ExecUSecs);

    //Build string for output file
    t = std::time(nullptr);
    tm = *std::localtime(&t);

    outFileStream<<"/mnt/sdb/data/Freq_data_"<<std::put_time(&tm, "%Y-%m-%d-%H-%M-%S")<<".spec";
    auto outFileStringB = outFileStream.str();

    // Output to be collected by CLI and sent to he6cres_db. 
    cout << "file_in_acq:" << outputs<< ",";
    cout << "file_path:" << outFileStringB<< ",";
    cout << "packets:" << RxPackets<< ",";
    cout << "file_size_mb:" << RxBytes / B1M << "\n";

    outFileStream.str("");
    outFileStream.clear();

    //Write output file in separate thread
    thread th2(fileWriter(), outFileStringB, sdb_datablock, RxPackets);

    //Reset receiver counters
    RxBytes = 0;
    RxPackets = 0;

    outputs ++; //increment # of output files written
    sdb_iter = sdb_datablock.begin(); //reset iterator to overwrite datablock on next pass

    if (outputs == intervals){ //join the thread (i.e. wait for it to finish) on final output
      th2.join();
      break;
    }
    else th2.detach(); //detach threads that will finish before main program

    UpdateTimer.now();
    USecs = UpdateTimer.timeus();

    while(USecs < intervalUs){
      //pull individual packet off the network interface
      int ReadSize = Receive.receive(buffer, BUFFERSIZE);

      if (ReadSize > 0) {
        //copy bytes from the buffer to the memmory position indicated by iter
        std::copy (buffer, buffer+BUFFERSIZE, sdc_iter);
        sdc_iter += BUFFERSIZE;  //advance the iterator to prep for buffering the next packet

        //increment counters for performance monitoring
        RxBytes += ReadSize;
        RxPackets++;
      }

      //update timer every 100 packets (~20k packets/sec => 100 packets = 5 ms
      if ((RxPackets % 100) == 0) USecs = UpdateTimer.timeus();
    } //end of while(USecs > intervalUs)

    //add bytes & packets recieved to totals
    RxTotPackets += RxPackets;
    RxBytesTotal += RxBytes;

    // //Output some performance stats to screen
    // printf("%" PRIu64 " Packets received, Total packets: %" PRIu64 "\n", RxPackets, RxTotPackets);
    // printf("Rx rate: %.2f Mbps, rx %" PRIu64 " MB (total: %" PRIu64 " MB) %" PRIu64 " usecs \n",
    //        RxBytes * 8.0 / (USecs / 1000000.0) / B1M, RxBytes / B1M, RxBytesTotal / B1M, USecs);
    // ExecUSecs = ExecTimer.timeus();
    // printf("Total execution time =  %" PRIu64 " usecs \n", ExecUSecs);

    //Build string for output file
    t = std::time(nullptr);
    tm = *std::localtime(&t);

    outFileStream<<"/mnt/sdc/data/Freq_data_"<<std::put_time(&tm, "%Y-%m-%d-%H-%M-%S")<<".spec";
    auto outFileStringC = outFileStream.str();
      
    // Output to be collected by CLI and sent to he6cres_db. 
    cout << "file_in_acq:" << outputs<< ",";
    cout << "file_path:" << outFileStringC<< ",";
    cout << "packets:" << RxPackets<< ",";
    cout << "file_size_mb:" << RxBytes / B1M << "\n";

    outFileStream.str("");
    outFileStream.clear();

    //Write output file in separate thread
    thread th3(fileWriter(), outFileStringC, sdc_datablock, RxPackets);

    UpdateTimer.now();

    //Reset receiver counters
    RxBytes = 0;
    RxPackets = 0;

    outputs ++; //increment # of output files written
    sdc_iter = sdc_datablock.begin(); //reset iterator to overwrite datablock on next pass

    if (outputs == intervals){ //join the thread (i.e. wait for it to finish) on final output
      th3.join();
    }
    else th3.detach(); //detach threads that will finish before main program

    UpdateTimer.now();
    USecs = UpdateTimer.timeus();

    while(USecs < intervalUs){
      //pull individual packet off the network interface
      int ReadSize = Receive.receive(buffer, BUFFERSIZE);

      if (ReadSize > 0) {
        //copy bytes from the buffer to the memmory position indicated by iter
        std::copy (buffer, buffer+BUFFERSIZE, sdc_iter);
        sdc_iter += BUFFERSIZE;  //advance the iterator to prep for buffering the next packet

        //increment counters for performance monitoring
        RxBytes += ReadSize;
        RxPackets++;
      }

      //update timer every 100 packets (~20k packets/sec => 100 packets = 5 ms
      if ((RxPackets % 100) == 0) USecs = UpdateTimer.timeus();
    } //end of while(USecs > intervalUs)

    //add bytes & packets recieved to totals
    RxTotPackets += RxPackets;
    RxBytesTotal += RxBytes;
    //Note (03282022). I am commenting this out to control the output. 
    // //Output some performance stats to screen
    // printf("%" PRIu64 " Packets received, Total packets: %" PRIu64 "\n", RxPackets, RxTotPackets);
    // printf("Rx rate: %.2f Mbps, rx %" PRIu64 " MB (total: %" PRIu64 " MB) %" PRIu64 " usecs \n",
    //        RxBytes * 8.0 / (USecs / 1000000.0) / B1M, RxBytes / B1M, RxBytesTotal / B1M, USecs);
    // ExecUSecs = ExecTimer.timeus();
    // printf("Total execution time =  %" PRIu64 " usecs \n", ExecUSecs);

    //Build string for output file
    t = std::time(nullptr);
    tm = *std::localtime(&t);

    outFileStream<<"/mnt/sdd/data/Freq_data_"<<std::put_time(&tm, "%Y-%m-%d-%H-%M-%S")<<".spec";
    auto outFileStringD = outFileStream.str();

    // Output to be collected by CLI and sent to he6cres_db. 
    cout << "file_in_acq:" << outputs<< ",";
    cout << "file_path:" << outFileStringD<< ",";
    cout << "packets:" << RxPackets<< ",";
    cout << "file_size_mb:" << RxBytes / B1M << "\n";

    outFileStream.str("");
    outFileStream.clear();

    //Write output file in separate thread
    thread th4(fileWriter(), outFileStringD, sdc_datablock, RxPackets);

    UpdateTimer.now();

    //Reset receiver counters
    RxBytes = 0;
    RxPackets = 0;

    outputs ++; //increment # of output files written
    sdd_iter = sdd_datablock.begin(); //reset iterator to overwrite datablock on next pass

    if (outputs == intervals){ //join the thread (i.e. wait for it to finish) on final output
      th4.join();
    }
    else th4.detach(); //detach threads that will finish before main program

  } //end of  while(outputs < intervals)
} //end of main ()

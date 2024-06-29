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
#include <chrono>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <ctime>
#include <unistd.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <assert.h>

using namespace std;

struct {
  int UDPPort{4003};
  int DataSize{5000}; // Was 5000
  int SocketBufferSize{12000000};
} Settings;


//Helper class to enable file output in separate thread from packet receiver
class fileWriter{
public:

  //overloading the () operator makes this a callable function object (for multithreading)
  void operator()(const string& path, const vector<char> &data, int packets, int BUFFERSIZE) {

    setpriority(PRIO_PROCESS, 0, -20);

    // static const int BUFFERSIZE{4128};
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
   
      //close output file
      fileout.close();
    }
  }
};


CLI::App app{"UDP receiver with 32 bit sequence number check."};

int main(int argc, char *argv[4]) {

  // Set this to highest priority: 
  setpriority(PRIO_PROCESS, 0, -20);

  char *nPtr = NULL;

  const int BUFFERSIZE = strtol(argv[1], &nPtr, 10); //buffersize
  int tot_packets = strtol(argv[2], &nPtr, 10); //number of packets to be collected per acquisition
  int drive = strtol(argv[3], &nPtr, 10);

  // int outputs = 0; //index variable for # of output files written

  const int B1M = 1000000;               //bytes per MB
  char buffer[BUFFERSIZE];               //buffer is declared as chars b/c they're 1 byte each

  uint64_t RxBytes{0};                   //bytes recieved in last interval
  uint64_t RxPackets{0};                 //packets received in last interval

  auto t = std::time(nullptr);           //time object for output file naming
  auto tm = *std::localtime(&t);         //system time object for output file naming
  std::ostringstream outFileStream;      //string for building output file name

  std::vector<char> sdb_datablock(700000000); //the large buffer for holding packets
  vector<char>::iterator sdb_iter = sdb_datablock.begin(); //iterator for navigating buffer vector

  int rec_time_s{1};
  int rec_time_us{0};

  //Set up socket and receiver to listen on it
  Socket::Endpoint local("10.66.192.50", 4003);

  // Set up Receiver. 
  UDPReceiver Receive(local);
  Receive.setBufferSizes(Settings.SocketBufferSize, Settings.SocketBufferSize);
  Receive.setRecvTimeout(rec_time_s, rec_time_us);

  while(RxPackets < tot_packets){
      //pull individual packet off the network interface
      int ReadSize = Receive.receive(buffer, BUFFERSIZE);
      // Be sure the ReadSize is the same as BUFFERSIZE. It should always be. 
//      assert(ReadSize == BUFFERSIZE);

      // Copy contents of small buffer to large mem block. 
      // Be sure this does what you think. 
      std::copy (buffer, buffer+BUFFERSIZE, sdb_iter);
      sdb_iter += ReadSize;  //advance the iterator to prep for buffering the next packet

      //increment counters for performance monitoring
      RxBytes += ReadSize;
      RxPackets++; 
      // }

    } //end of while(RxPackets < tot_packets)

    // Close the socket connection. 
    Receive.Close();
    
    //Build string for output file
    t = std::time(nullptr);
    tm = *std::localtime(&t);

    char *drives = "bcd";

    outFileStream<<"/mnt/sd" << drives[drive] <<"/data/Freq_data_"<<std::put_time(&tm, "%Y-%m-%d-%H-%M-%S")<<".spec";
    // outFileStream<<"/data/Freq_data_"<<std::put_time(&tm, "%Y-%m-%d-%H-%M-%S")<<".spec";
    auto outFileStringB = outFileStream.str();

    // Output to be collected by CLI and sent to he6cres_db. 
    cout << "file_path:" << outFileStringB<< ",";
    cout << "packets:" << RxPackets<< ",";
    cout << "file_size_mb:" << RxBytes / B1M ;

    outFileStream.str("");
    outFileStream.clear();

    //Write output file in separate thread
    thread th2(fileWriter(), outFileStringB, sdb_datablock, RxPackets, BUFFERSIZE);

    // std::chrono::milliseconds downtime(1000); // Currently 1s. How long to rest between threads. 
    // std::this_thread::sleep_for(downtime);

    th2.join();

} //end of main ()

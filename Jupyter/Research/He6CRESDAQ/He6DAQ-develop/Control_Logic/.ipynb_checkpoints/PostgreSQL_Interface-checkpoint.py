import pandas as pd
import numpy as np
import typing
from typing import List
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
from datetime import datetime
from pathlib import Path


psycopg2.extensions.register_adapter(np.int64, AsIs)


def he6cres_db_connection():

    # Connect to the he6cres_db
    connection = psycopg2.connect(
        user="postgres",
        password="chirality",
        host="10.66.192.47",
        port="5432",
        database="he6cres_db",
    )
    return connection


def he6cres_db_query(query: str) -> typing.Union[None, pd.DataFrame]:
    connection = False
    try:

        connection = he6cres_db_connection()

        # Create a cursor to perform database operations
        cursor = connection.cursor()

        # Execute a sql_command
        cursor.execute(query)
        cols = [desc[0] for desc in cursor.description]
        query_result = pd.DataFrame(cursor.fetchall(), columns=cols)

    except Exception as error:
        print("Error while connecting to he6cres_db", error)
        query_result = None

    finally:
        if connection:
            cursor.close()
            connection.close()
            #print("Connection to he6cres_db is closed")

    return query_result


def format_udprx_output(udprx_output: str) -> List[dict]:

    # output = udprx_output.decode("utf-8").splitlines()

    spec_file_list = []
    for i, line in enumerate(udprx_output):

        # Fill this empty dict
        spec_dict = {
            "file_in_acq": None,
            "file_size_mb": None,
            "packets": None,
            "file_path": None,
        }
        for param in line.split(","):
            key = param.split(":")[0]
            value = param.split(":")[1]
            spec_dict[key] = value

        spec_file_list.append(spec_dict)

    return spec_file_list


def fill_he6cres_db(env_parameters: dict, spec_file_list: List[dict]) -> None:

    env_param_db = {k: v for k, v in env_parameters.items() if k != "slewing"}

    connection = False
    try:

        connection = he6cres_db_connection()

        # Create a cursor to perform database operations
        cursor = connection.cursor()
        print("\nConnected to he6cres_db.\n")

        env_param_db["num_spec_acq"] = len(spec_file_list)
        columns = env_param_db.keys()
        values = env_param_db.values()

        insert_statement = (
            "INSERT INTO he6cres_runs.run_log (%s) Values %s RETURNING run_id"
        )

        query = cursor.mogrify(
            insert_statement, (AsIs(",".join(columns)), tuple(values))
        )
        cursor.execute(query)
        connection.commit()

        print("Inserted env_parameters into he6cres_runs.run_log.\n")
        run_id = cursor.fetchone()[0]

        print("Assigned run_id:", run_id)

        for file_in_acq, spec_file_dict in enumerate(spec_file_list):

            spec_file_dict["file_in_acq"] = file_in_acq

            insert_statement = """INSERT INTO he6cres_runs.spec_files
                                (run_id, 
                                file_in_acq, 
                                packets, 
                                file_size_mb, 
                                file_path,
                                num_dropped_packets,
                                frac_of_packets_dropped,
                                num_gaps,
                                neg_gaps,
                                mean_gap,
                                std_gap,
                                max_gap, 
                                deleted
                                ) 
                                Values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING spec_id"""

            query = cursor.mogrify(
                insert_statement,
                (
                    run_id,
                    int(spec_file_dict["file_in_acq"]),
                    int(spec_file_dict["packets"]),
                    int(spec_file_dict["file_size_mb"]),
                    spec_file_dict["file_path"],
                    int(spec_file_dict["num_dropped_packets"]),
                    spec_file_dict["frac_of_packets_dropped"],
                    spec_file_dict["num_gaps"],
                    spec_file_dict["neg_gaps"],
                    spec_file_dict["mean_gap"],
                    spec_file_dict["std_gap"],
                    spec_file_dict["max_gap"],
                    bool(spec_file_dict["deleted"]),
                ),
            )

            cursor.execute(query)
            connection.commit()
            print("file_in_acq: ", file_in_acq, "spec_id: ", cursor.fetchone()[0])

        print(
            "\nInserted {} files into he6cres_runs.spec_files.".format(
                len(spec_file_list)
            )
        )

    except Exception as error:
        print("Error while connecting to he6cres_db", error)
        query_result = None

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("\nConnection to he6cres_db closed.")

    return None


def write_packet_report_to_he6db(spec_file_list: List[dict]) -> None:

    connection = False
    try:

        connection = he6cres_db_connection()

        # Create a cursor to perform database operations
        cursor = connection.cursor()
        print("\nConnected to he6cres_db.\n")

        total_files = len(spec_file_list)
        for i, spec_file_dict in enumerate(spec_file_list):

            print("Writing packet report to db for file {}/{}".format(i, total_files))

            insert_statement = """UPDATE he6cres_runs.spec_files
                                  SET 
                                    num_dropped_packets = %s,
                                    frac_of_packets_dropped = %s,
                                    num_gaps = %s, 
                                    neg_gaps = %s, 
                                    mean_gap = %s, 
                                    std_gap = %s, 
                                    max_gap = %s
                                  WHERE spec_id = %s """.format()

            query = cursor.mogrify(
                insert_statement,
                (
                    int(spec_file_dict["num_dropped_packets"]),
                    spec_file_dict["frac_of_packets_dropped"],
                    spec_file_dict["num_gaps"],
                    spec_file_dict["neg_gaps"],
                    spec_file_dict["mean_gap"],
                    spec_file_dict["std_gap"],
                    spec_file_dict["max_gap"],
                    spec_file_dict["spec_id"],
                ),
            )
            cursor.execute(query)
            connection.commit()

        print(
            "\nInserted {} files into he6cres_runs.spec_files.".format(
                len(spec_file_list)
            )
        )

    except Exception as error:
        print("Error while connecting to he6cres_db", error)
        query_result = None

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("\nConnection to he6cres_db closed.")

    return None


def mark_spec_files_as_deleted(run_id):

    connection = False
    try:

        connection = he6cres_db_connection()

        # Create a cursor to perform database operations
        cursor = connection.cursor()
        print("\nConnected to he6cres_db.\n")

        insert_statement = """UPDATE he6cres_runs.spec_files
                              SET 
                                deleted = True
                              WHERE run_id = {}""".format(
            run_id
        )

        cursor.execute(insert_statement)
        connection.commit()

    except Exception as error:
        print("Error while connecting to he6cres_db", error)
        query_result = None

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("\nConnection to he6cres_db closed.")

    return None


def backup_he6cres_run_tables(base_path, limit=1e6):

    today = datetime.today().strftime("%m-%d-%Y")

    base_path = Path(base_path)
    backup_dir_path = base_path / Path(f"he6cres_runs_db_backup_{today}")
    backup_dir_path.mkdir()

    table_names = ["run_log", "spec_files", "monitor", "nmr"]

    for table_name in table_names:

        csv_path = backup_dir_path / Path(f"{table_name}_{today}.csv")

        query = """SELECT *
                   FROM he6cres_runs.{}
                   ORDER BY created_at DESC
                   LIMIT {}
                """.format(
            table_name, int(limit)
        )

        table = he6cres_db_query(query)

        print(f"{table_name}: Writing {len(table)} rows.\n")
        table.to_csv(csv_path, index=False)

    return None

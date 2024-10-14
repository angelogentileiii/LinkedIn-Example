#SEC FTD LAMBDA

import io
import os
import re
import boto3
import pandas as pd
import numpy as np
from datetime import datetime
from zipfile import ZipFile
from dbConnect import mysqlConnect

# for updating to the most recent report added to the bucket
def get_recent_ftd_zip(s3_client, bucket_name, key):
    try:
        print('Reading from S3 Bucket...')
        response = s3_client.get_object(Bucket=bucket_name, Key=key)

        # Extract zip file from response
        ftd_file = response['Body']

        if not ftd_file:
            raise ValueError('There are no FTD zip files in the bucket.')

        print('Extracting the FTD zipfile...')
        ftd_content = io.BytesIO(ftd_file.read())

        return ftd_content

    except Exception as e:
        print(e)
        print('Error retrieving FTD Data from bucket.' + \
              'Ensure report exists and is in the same region as this bucket.')
        raise(e)

# Function to unzip the FTD report from bucket
def unzip_file(zip_file):
    try:
        with ZipFile(zip_file, 'r') as ftd_ref:
            # only one file in each zip from SEC
            ftd_report = ftd_ref.namelist()[0]

            # read file only in memory
            with ftd_ref.open(ftd_report) as file:
                print('Unzipping FTD Report...')
                ftd_content = file.read()

        return ftd_report, ftd_content
    
    except Exception as e:
        print('Error unzipping the file or reading its contents.')
        print(e)

def define_update_revision(report_name, date):
    pattern = r'cnsfails(\d{4})(\d{2})([ab])'

    match = re.match(pattern, report_name)

    if match:
        # Pull out groups from report name
        year = int(match.group(1))

        # Calculate the week number based upon the year/month in report name
        week_number = date.isocalendar()[1]

        week_number %= 52

        if week_number == 0:
            week_number = 52

        # Formatted string to input as update_revision
        update_revision = f"{year}w{week_number:02d}"

        print('Update Revision Calculated: ', update_revision)

        return update_revision
    else:
        raise ValueError('FTD report_name does not match expected pattern.')


# clean all data prior to insertion
def preprocess_ftd_report(rep_name, rep_content):
    try:
        # Create a file-like object from the content
        ftd_content = io.BytesIO(rep_content)

        # Read file from memory and parse by delimiter
        # First row are column headers
        ftd_data = pd.read_csv(ftd_content, sep="|", header=0)

        # Exclude last two rows (total records and total shares overall)
        ftd_data = ftd_data.iloc[:-2]
        
        ftd_data = ftd_data.rename(columns={
            'SETTLEMENT DATE': 'SETTLE_DATE',
            'CUSIP': 'CUSIP',
            'SYMBOL': 'SYMBOL',
            'COMP_NAME': 'COMP_NAME',
            'QUANTITY (FAILS)': 'QUANTITY',
            'PRICE': 'PRICE'
        })

        convert_keys = ['QUANTITY', 'PRICE']

        # Convert values to numeric values
        for col in convert_keys:
            ftd_data[col] = pd.to_numeric(ftd_data[col], errors='coerce')

        # Conver the settle date to a datetime object
        ftd_data['SETTLE_DATE'] = ftd_data['SETTLE_DATE'].apply(lambda x: datetime.strptime(x, '%Y%m%d').date())

        max_date = max(set(ftd_data['SETTLE_DATE']))
        print(max_date)
        # Convert NaN to None for MySQL DB
        ftd_data = ftd_data.replace({np.nan: None})

        # Add update revision column to DF
        update_rev = define_update_revision(rep_name, max_date)
        ftd_data['UPDATE_REVISION'] = update_rev

        return ftd_data
    
    except Exception as e:
        print('Error processing the data retrieved from FTD Report.')
        print(e)


def insert_into_db(db_connection, ftd_data):
    cursor = db_connection.cursor()

    try:
        # Convert DataFrame to list of tuples
        data_rows = [tuple(r) for r in ftd_data.to_numpy()]
        print(data_rows[0])
        
        sql_query = '''
            INSERT INTO sec_ftd_infotable
                (SETTLE_DATE, 
                CUSIP, 
                SYMBOL,  
                QUANTITY,
                COMP_NAME, 
                PRICE,
                UPDATE_REVISION)
            VALUES
                ({})
            ON DUPLICATE KEY UPDATE
                SETTLE_DATE = VALUES(SETTLE_DATE),
                CUSIP = VALUES(CUSIP),
                SYMBOL = VALUES(SYMBOL),
                QUANTITY = VALUES(QUANTITY),
                COMP_NAME = VALUES(COMP_NAME),
                PRICE = VALUES(PRICE),
                UPDATE_REVISION = VALUES(UPDATE_REVISION);
            '''.format(','.join('%s' for _ in range(7)))

        # Execute the query with parameters for security
        cursor.executemany(sql_query, data_rows)

        db_connection.commit()
        print("Data appended to ftd model and committed successfully.")
    
    except Exception as e:
        # roll back if an errors occur during upsert
        db_connection.rollback()
        print('Data was not properly inserted into database table. See error response for more information.')
        raise ValueError(e)
    
    finally:
        db_connection.close()

def ftd_handler(event, context):
    try:
        # Initialize environment variables (Still needed)
        MAIN_DB = os.environ['MAIN_DB']
        REGION = os.environ['REGION']

        # Instantiate lambda client?
        lambda_client = boto3.client('lambda')

        # Instantiates s3 client
        s3_client = boto3.client('s3')
        
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

        # Only for most recent report added to bucket
        ftd_rep = get_recent_ftd_zip(s3_client, bucket_name, key)
        rep_name, rep_content = unzip_file(ftd_rep)
        processed_ftd = preprocess_ftd_report(rep_name, rep_content)

        # Connect to mySQL database to upsert data
        connection = mysqlConnect.connect_to_db(MAIN_DB, REGION, "pymysql")

        insert_into_db(connection, processed_ftd)

        # Variable for successful response
        num_rows = len(processed_ftd)

        print('DB Append completed successfully. See response for more detailed info.')

        return {
            "status_code": 200,
            "body": {
                "message": "DB Append executed with no errors.",
                "bucket_name": bucket_name,
                "report_inserted": rep_name,
                "inserted_rows": num_rows
            }
        }
        
    except Exception as e:
        print('Error during handling of FTD report. Check handle_ftd_report function for errors.')
        raise(e)
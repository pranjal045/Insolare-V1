import os
from data_pipeline.ingestion import s3_connector, sql_connector, email_parser

FETCH = False # make it true if wanna bring-in/gather the new items on cloud

if __name__ == '__main__':
    if(FETCH):
        s3 = s3_connector.S3Connector('your-s3-bucket-name')
        files_in_s3 = s3.list_files()
        for file in files_in_s3:
            s3.download_file(file, os.path.join('raw_document', file))

        sql = sql_connector.SQLConnector()
        files_in_sql = sql.query("SELECT * FROM files")
        for file in files_in_sql:
            with open(os.path.join('raw_document', file[0]), 'wb') as f:
                f.write(file[1])

        email = email_parser.EmailParser("imap.gmail.com", "your-email@gmail.com", "your-password")
        files_in_email = email.fetch_emails()
        for file in files_in_email:
            with open(os.path.join('raw_document', file['filename']), 'wb') as f:
                f.write(file['data'])
    else:
        print("No files to fetch.")

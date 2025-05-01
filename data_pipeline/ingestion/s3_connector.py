import boto3
import os

class S3Connector:
    def __init__(self, bucket_name, region_name='us-east-1'):
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3', region_name=region_name,
                               aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                               aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

    def download_file(self, s3_key, local_path):
        try:
            self.s3.download_file(self.bucket_name, s3_key, local_path)
            print(f"Downloaded {s3_key} to {local_path}")
        except Exception as e:
            print(f"Error downloading file: {e}")

if __name__ == '__main__':
    bucket = 'your-s3-bucket-name'
    connector = S3Connector(bucket)
    connector.download_file('path/to/your/file.pdf', 'data/file.pdf')
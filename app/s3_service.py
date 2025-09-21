import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class TimeWebS3Service:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                endpoint_url=os.getenv('AWS_S3_ENDPOINT_URL'),
                region_name=os.getenv('AWS_REGION', 'ru-1')
            )
            self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')

            self.s3_client.head_bucket(Bucket=self.bucket_name)

        except NoCredentialsError:
            raise HTTPException(status_code=500, detail="AWS credentials not configured")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise HTTPException(status_code=500, detail="S3 bucket not found")
            else:
                raise HTTPException(status_code=500, detail=f"S3 connection error: {error_code}")

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:

        try:

            if file.size == 0:
                raise HTTPException(status_code=400, detail="File is empty")

            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'bin'
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"

            s3_key = f"{folder}/{unique_filename}" if folder else unique_filename

            content = await file.read()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream',
                ACL='public-read'
            )

            file_url = f"https://{self.bucket_name}.s3.{os.getenv('AWS_REGION')}.twcstorage.ru/{s3_key}"
            return file_url

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

    async def delete_file(self, file_url: str) -> bool:

        try:

            if self.bucket_name in file_url:
                file_key = file_url.split(f"{self.bucket_name}.s3.")[1].split('/')[1:]
                file_key = '/'.join(file_key)

                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return True
            return False
        except ClientError:
            return False

    async def list_files(self, folder: str = "") -> list:

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=folder + '/' if folder else ''
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            print(f"Error listing files: {e}")
            return []


s3_service = TimeWebS3Service()

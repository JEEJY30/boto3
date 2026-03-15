import argparse
import boto3
import logging
import json
from os import getenv
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import requests
import magic
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_client():
    """Initializes and returns a Boto3 S3 client."""
    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=getenv("aws_access_key_id"),
            aws_secret_access_key=getenv("aws_secret_access_key"),
            aws_session_token=getenv("aws_session_token"),
            region_name=getenv("aws_region") # Default to us-east-1 if not set
        )
        # Check credentials by making a simple API call
        client.list_buckets()
        logging.info("S3 client initialized successfully.")
        return client
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidClientTokenId' or e.response['Error']['Code'] == 'SignatureDoesNotMatch':
             logging.error("Invalid AWS credentials. Please check your .env file.")
        else:
             logging.error(f"Error initializing S3 client: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during client initialization: {e}")
        return None


def list_buckets(s3_client):
    """Lists all S3 buckets."""
    try:
        response = s3_client.list_buckets()
        print("Existing buckets:")
        for bucket in response['Buckets']:
            print(f"  {bucket['Name']}")
        return True
    except ClientError as e:
        logging.error(f"Error listing buckets: {e}")
        return False

def create_bucket(s3_client, bucket_name, region=None):
    region = os.getenv("aws_region")
    """Creates a new S3 bucket."""
    if bucket_exists(s3_client, bucket_name):
        logging.info(f"Bucket '{bucket_name}' already exists.")
        return True

    try:
        if region:
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        else:
            s3_client.create_bucket(Bucket=bucket_name)

        logging.info(f"Bucket '{bucket_name}' created successfully.")
    except ClientError as e:
        logging.error(f"Error creating bucket: {e}")
        return False
    return True


def delete_bucket(s3_client, bucket_name):
    """Deletes an S3 bucket."""
    if not bucket_exists(s3_client, bucket_name):
        logging.warning(f"Bucket '{bucket_name}' does not exist.")
        return False
    try:
        # For a real-world tool, you would need to handle object deletion first.
        s3_client.delete_bucket(Bucket=bucket_name)
        logging.info(f"Bucket '{bucket_name}' deleted successfully.")
        return True
    except ClientError as e:
        logging.error(f"Error deleting bucket: {e}")
        return False

def bucket_exists(s3_client, bucket_name):
    """Checks if a bucket exists."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # A '403' can mean you don't have permissions, but the bucket exists
            logging.warning(f"Could not definitively check bucket existence for '{bucket_name}': {e}")
            return False

def upload_local_file_to_s3(s3_client, bucket_name, file_path, object_name=None):
    """Uploads a local file to S3 with MIME type validation."""
    if not bucket_exists(s3_client, bucket_name):
        logging.error(f"Bucket '{bucket_name}' does not exist.")
        return False

    allowed_mime_types = ['image/bmp', 'image/jpeg', 'image/png', 'image/webp', 'video/mp4']

    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            file_content = f.read()

        mime_type = magic.from_buffer(file_content, mime=True)
        logging.info(f"Detected MIME type: {mime_type}")

        if mime_type not in allowed_mime_types:
            logging.error(f"Unsupported file type: {mime_type}. Allowed types: {', '.join(allowed_mime_types)}")
            return False

        s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=file_content, ContentType=mime_type)
        logging.info(f"File '{object_name}' uploaded to bucket '{bucket_name}' successfully.")
        return True

    except Exception as e:
        logging.error(f"Error uploading local file: {e}")
        return False
    
def download_file_from_s3(s3_client, bucket_name, object_name, download_path=None):
    """Downloads a file from S3 to local disk."""
    if download_path is None:
        download_path = object_name  # Save with same name as object

    try:
        s3_client.download_file(bucket_name, object_name, download_path)
        logging.info(f"File '{object_name}' downloaded from bucket '{bucket_name}' to '{download_path}'.")
        return True
    except ClientError as e:
        logging.error(f"Error downloading file from S3: {e}")
        return False

def set_object_access_policy(s3_client, bucket_name, object_name):
    """Sets a public-read ACL on an S3 object."""
    if not bucket_exists(s3_client, bucket_name):
        logging.error(f"Bucket '{bucket_name}' does not exist.")
        return False
    try:
        s3_client.put_object_acl(Bucket=bucket_name, Key=object_name, ACL='public-read')
        logging.info(f"Set public-read ACL for object '{object_name}' in bucket '{bucket_name}'.")
        return True
    except ClientError as e:
        logging.error(f"Error setting object ACL: {e}")
        return False

def generate_public_read_policy(bucket_name):
    """Generates a JSON string for a public read policy."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    return json.dumps(policy)

def create_bucket_policy(s3_client, bucket_name):
    """Creates and applies a public read policy to a bucket after removing public access blocks."""
    if not bucket_exists(s3_client, bucket_name):
        logging.error(f"Bucket '{bucket_name}' does not exist.")
        return False
    try:
        # This is the key part to allow public policies
        s3_client.delete_public_access_block(Bucket=bucket_name)
        logging.info(f"Public access block for '{bucket_name}' has been deleted.")

        policy = generate_public_read_policy(bucket_name)
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy)
        logging.info(f"Public read policy applied to bucket '{bucket_name}'.")
        return True
    except ClientError as e:
        logging.error(f"Error creating bucket policy: {e}")
        return False

def read_bucket_policy(s3_client, bucket_name):
    """Reads and prints the policy of a bucket."""
    if not bucket_exists(s3_client, bucket_name):
        logging.error(f"Bucket '{bucket_name}' does not exist.")
        return False
    try:
        policy_response = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy_str = policy_response.get('Policy')
        if policy_str:
            print(f"Policy for bucket '{bucket_name}':")
            print(json.dumps(json.loads(policy_str), indent=4))
            return policy_str
        else:
            logging.info(f"Bucket '{bucket_name}' has a policy entry, but it is empty.")
            return None
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            logging.warning(f"Bucket '{bucket_name}' does not have a policy.")
            return None
        else:
            logging.error(f"Error reading bucket policy: {e}")
            return None


def main():
    """Main function to parse arguments and call appropriate S3 functions."""
    parser = argparse.ArgumentParser(description="A comfortable CLI tool to work with S3 Buckets.")
    subparsers = parser.add_subparsers(dest="command", help="Available S3 commands", required=True)

    # list-buckets
    subparsers.add_parser("list-buckets", help="List all S3 buckets.")

    # create-bucket
    parser_create = subparsers.add_parser("create-bucket", help="Create a new S3 bucket.")
    parser_create.add_argument("bucket_name", help="The name of the bucket to create.")
    parser_create.add_argument("--region", help="The AWS region for the bucket (e.g., 'us-west-2').")

    # delete-bucket
    parser_delete = subparsers.add_parser("delete-bucket", help="Delete an S3 bucket.")
    parser_delete.add_argument("bucket_name", help="The name of the bucket to delete.")

    # bucket-exists
    parser_exists = subparsers.add_parser("bucket-exists", help="Check if a bucket exists.")
    parser_exists.add_argument("bucket_name", help="The name of the bucket to check.")

    # upload-file
    # upload-local
    parser_upload_local = subparsers.add_parser("upload-local", help="Upload a local file to S3.")
    parser_upload_local.add_argument("bucket_name", help="Destination bucket")
    parser_upload_local.add_argument("file_path", help="Path to the local file")
    parser_upload_local.add_argument("--name", help="Optional object name in S3")

    # download-from-s3
    parser_download = subparsers.add_parser("download-from-s3", help="Download a file from S3.")
    parser_download.add_argument("bucket_name", help="Source bucket")
    parser_download.add_argument("object_name", help="Object key (filename in S3)")
    parser_download.add_argument("--path", help="Local path to save the file (defaults to object name)")

    # set-object-policy
    parser_set_policy = subparsers.add_parser("set-object-policy", help="Set a public-read ACL on an object.")
    parser_set_policy.add_argument("bucket_name", help="The bucket name.")
    parser_set_policy.add_argument("object_name", help="The object key (filename).")

    # create-bucket-policy
    parser_create_bpolicy = subparsers.add_parser("create-bucket-policy", help="Apply a public-read policy to a bucket.")
    parser_create_bpolicy.add_argument("bucket_name", help="The bucket name.")

    # read-bucket-policy
    parser_read_bpolicy = subparsers.add_parser("read-bucket-policy", help="Read the policy of a bucket.")
    parser_read_bpolicy.add_argument("bucket_name", help="The bucket name.")

    args = parser.parse_args()
    s3_client = init_client()

    if not s3_client:
        logging.error("Could not initialize S3 client. Exiting.")
        return

    if args.command == "list-buckets":
        list_buckets(s3_client)
    elif args.command == "create-bucket":
        create_bucket(s3_client, args.bucket_name, args.region)
    elif args.command == "delete-bucket":
        delete_bucket(s3_client, args.bucket_name)
    elif args.command == "bucket-exists":
        if bucket_exists(s3_client, args.bucket_name):
            logging.info(f"Bucket '{args.bucket_name}' exists.")
        else:
            # The bucket_exists function already logs relevant warnings/errors
            logging.info(f"Bucket '{args.bucket_name}' does not exist or you lack permissions to see it.")
    elif args.command == "upload-local":
        upload_local_file_to_s3(s3_client, args.bucket_name, args.file_path, args.name)
    elif args.command == "download-from-s3":
        download_file_from_s3(s3_client, args.bucket_name, args.object_name, args.path)
    elif args.command == "set-object-policy":
        set_object_access_policy(s3_client, args.bucket_name, args.object_name)
    elif args.command == "create-bucket-policy":
        create_bucket_policy(s3_client, args.bucket_name)
    elif args.command == "read-bucket-policy":
        read_bucket_policy(s3_client, args.bucket_name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
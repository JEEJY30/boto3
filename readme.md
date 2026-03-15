# S3 CLI Tool

A convenient command-line tool for managing **AWS S3 buckets and objects**, supporting local file uploads, downloads, bucket management, and public access policies.  

This tool includes **MIME type validation** for uploaded files and simplifies S3 bucket policy handling.

---

## Features

- List all S3 buckets.
- Create and delete S3 buckets.
- Check if a bucket exists.
- Upload local files to S3 (`jpeg`, `png`, `bmp`, `webp`, `mp4`).
- Download files from S3.
- Set public-read access on individual objects.
- Apply public-read bucket policies.
- Read existing bucket policies.

---

## Prerequisites

- Python 3.8+
- AWS account and credentials with S3 access.
- Required Python packages:

```bash
poetry add boto3 python-dotenv requests python-magic
brew install libmagic
```

# Commands

List buckets
```bash
python s3_cli.py list-buckets
```
Create a bucket
```bash
python s3_cli.py create-bucket my-bucket --region us-west-2
```
Delete a bucket
```bash
python s3_cli.py delete-bucket my-bucket
```
Check if a bucket exists
```bash
python s3_cli.py bucket-exists my-bucket
```
Upload local file to S3
```bash
python s3_cli.py upload-local my-bucket /path/to/image.jpeg
```
Optional: specify object name in S3:
```bash
python s3_cli.py upload-local my-bucket /path/to/image.jpeg --name holiday.jpeg
```
Download file from S3
```bash
python s3_cli.py download-from-s3 my-bucket holiday.jpeg
```
Optional: save to custom path:
```bash
python s3_cli.py download-from-s3 my-bucket holiday.jpeg --path /Users/user/Downloads/
```
Set public-read access on an object
```bash
python s3_cli.py set-object-policy my-bucket holiday.jpeg
```
Apply public-read policy to a bucket
```bash
python s3_cli.py create-bucket-policy my-bucket
```
Read bucket policy
```bash
python s3_cli.py read-bucket-policy my-bucket
```
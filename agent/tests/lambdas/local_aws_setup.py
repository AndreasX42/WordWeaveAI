#!/usr/bin/env python3
"""
LocalStack AWS Setup Script
Sets up all AWS resources needed for local end-to-end testing
"""

import json
import os

import boto3

# LocalStack configuration
LOCALSTACK_ENDPOINT = "http://localhost:4566"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "test"
AWS_SECRET_ACCESS_KEY = "test"


def get_localstack_client(service_name: str):
    """Get a boto3 client configured for LocalStack"""
    return boto3.client(
        service_name,
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def create_dynamodb_tables():
    """Create all DynamoDB tables needed for the application"""
    dynamodb = get_localstack_client("dynamodb")

    tables = [
        {
            "TableName": "vocabDataTable",
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "connectionsTable",
            "KeySchema": [{"AttributeName": "connectionId", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "connectionId", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "userDataTable",
            "KeySchema": [{"AttributeName": "userId", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "userId", "AttributeType": "S"}],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "vocabListTable",
            "KeySchema": [{"AttributeName": "listId", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "listId", "AttributeType": "S"}],
            "BillingMode": "PAY_PER_REQUEST",
        },
        {
            "TableName": "vocabMediaTable",
            "KeySchema": [{"AttributeName": "mediaId", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "mediaId", "AttributeType": "S"}
            ],
            "BillingMode": "PAY_PER_REQUEST",
        },
    ]

    for table_config in tables:
        try:
            dynamodb.create_table(**table_config)
            print(f"✅ Created table: {table_config['TableName']}")

            # Wait for table to be active
            waiter = dynamodb.get_waiter("table_exists")
            waiter.wait(TableName=table_config["TableName"])
            print(f"✅ Table {table_config['TableName']} is active")

        except dynamodb.exceptions.ResourceInUseException:
            print(f"⚠️  Table {table_config['TableName']} already exists")
        except Exception as e:
            print(f"❌ Error creating table {table_config['TableName']}: {e}")


def create_s3_bucket():
    """Create S3 bucket for media storage"""
    s3 = get_localstack_client("s3")

    bucket_name = "vocab-media-bucket-local"

    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created S3 bucket: {bucket_name}")

        # Enable CORS for local development
        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                    "AllowedOrigins": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }
        s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
        print(f"✅ Configured CORS for bucket: {bucket_name}")

    except s3.exceptions.BucketAlreadyExists:
        print(f"⚠️  S3 bucket {bucket_name} already exists")
    except Exception as e:
        print(f"❌ Error creating S3 bucket {bucket_name}: {e}")


def create_sqs_queue():
    """Create SQS queue for async processing"""
    sqs = get_localstack_client("sqs")

    queue_name = "vocab-processing-queue"

    try:
        response = sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                "DelaySeconds": "0",
                "MessageRetentionPeriod": "1209600",  # 14 days
                "VisibilityTimeout": "300",  # Fixed parameter name
            },
        )
        print(f"✅ Created SQS queue: {queue_name}")
        print(f"   Queue URL: {response['QueueUrl']}")

    except Exception as e:
        print(f"❌ Error creating SQS queue {queue_name}: {e}")


def create_lambda_functions():
    """Create Lambda functions for WebSocket handling"""
    lambda_client = get_localstack_client("lambda")

    # Create a simple WebSocket handler function
    function_code = """
import json
import boto3

def lambda_handler(event, context):
    connection_id = event.get('requestContext', {}).get('connectionId')
    route_key = event.get('requestContext', {}).get('routeKey')
    
    print(f"WebSocket event - Connection: {connection_id}, Route: {route_key}")
    
    # Store connection info in DynamoDB
    if route_key == '$connect':
        dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4566')
        table = dynamodb.Table('connectionsTable')
        table.put_item(Item={'connectionId': connection_id, 'status': 'connected'})
        
    elif route_key == '$disconnect':
        dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4566')
        table = dynamodb.Table('connectionsTable')
        table.delete_item(Key={'connectionId': connection_id})
    
    return {'statusCode': 200, 'body': json.dumps('OK')}
"""

    # Create proper ZIP file for Lambda
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("index.py", function_code)
    zip_buffer.seek(0)

    functions = [
        {
            "FunctionName": "websocket-connect-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "index.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket connect handler for local testing",
        },
        {
            "FunctionName": "websocket-disconnect-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "index.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket disconnect handler for local testing",
        },
        {
            "FunctionName": "websocket-default-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "index.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket default handler for local testing",
        },
    ]

    for func_config in functions:
        try:
            response = lambda_client.create_function(**func_config)
            print(f"✅ Created Lambda function: {func_config['FunctionName']}")
            print(f"   Function ARN: {response['FunctionArn']}")

        except lambda_client.exceptions.ResourceConflictException:
            print(f"⚠️  Lambda function {func_config['FunctionName']} already exists")
        except Exception as e:
            print(
                f"❌ Error creating Lambda function {func_config['FunctionName']}: {e}"
            )


def create_websocket_api():
    """Create WebSocket API Gateway (Not available in free LocalStack)"""
    print("⚠️  WebSocket API Gateway requires LocalStack Pro")
    print("   For full WebSocket testing, consider upgrading to LocalStack Pro")
    print("   Current tests will focus on core functionality without WebSocket API")

    # Return a mock endpoint for testing purposes
    return "ws://localhost:4566/mock-websocket-endpoint"


def create_iam_role():
    """Create IAM role for Lambda functions"""
    iam = get_localstack_client("iam")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        iam.create_role(
            RoleName="lambda-execution-role",
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Lambda execution role for local testing",
        )
        print("✅ Created IAM role: lambda-execution-role")

        # Attach basic execution policy
        iam.attach_role_policy(
            RoleName="lambda-execution-role",
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        print("✅ Attached basic execution policy")

    except iam.exceptions.EntityAlreadyExistsException:
        print("⚠️  IAM role lambda-execution-role already exists")
    except Exception as e:
        print(f"❌ Error creating IAM role: {e}")


def setup_local_environment():
    """Set up environment variables for local testing"""
    os.environ["AWS_ENDPOINT_URL"] = LOCALSTACK_ENDPOINT
    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
    os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "local-test-function"
    os.environ["VOCAB_DATA_TABLE_NAME"] = "vocabDataTable"
    os.environ["CONNECTIONS_TABLE_NAME"] = "connectionsTable"
    os.environ["S3_MEDIA_BUCKET_NAME"] = "vocab-media-bucket-local"

    print("✅ Set up local environment variables")


def main():
    """Main setup function"""
    print("🚀 Starting LocalStack AWS setup...")
    print("=" * 50)

    # Check if LocalStack is running
    try:
        sts = get_localstack_client("sts")
        sts.get_caller_identity()
        print("✅ LocalStack is running")
    except Exception as e:
        print(f"❌ LocalStack is not running or not accessible: {e}")
        print("Please start LocalStack with: docker-compose up -d")
        return

    # Set up environment
    setup_local_environment()

    # Create resources
    print("\n📚 Creating DynamoDB tables...")
    create_dynamodb_tables()

    print("\n💾 Creating S3 bucket...")
    create_s3_bucket()

    print("\n📬 Creating SQS queue...")
    create_sqs_queue()

    print("\n🔑 Creating IAM role...")
    create_iam_role()

    print("\n⚡ Creating Lambda functions...")
    create_lambda_functions()

    print("\n🔌 Creating WebSocket API...")
    websocket_endpoint = create_websocket_api()

    print("\n" + "=" * 50)
    print("✅ LocalStack setup complete!")
    print(f"🔌 WebSocket endpoint: {websocket_endpoint}")
    print(f"🌐 LocalStack dashboard: http://localhost:4566")
    print(
        f"📊 DynamoDB tables: vocabDataTable, connectionsTable, userDataTable, vocabListTable, vocabMediaTable"
    )
    print(f"💾 S3 bucket: vocab-media-bucket-local")
    print(f"📬 SQS queue: vocab-processing-queue")
    print("\n🧪 Ready for end-to-end testing!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Enhanced LocalStack AWS Setup Script
Sets up all AWS resources needed for local end-to-end testing with validation and error handling
"""

import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

# LocalStack configuration
LOCALSTACK_ENDPOINT = "http://localhost:4566"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "test"
AWS_SECRET_ACCESS_KEY = "test"

# Core AWS configuration variables that should be set
CORE_AWS_VARS = [
    "AWS_ENDPOINT_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
]


def validate_configuration():
    """Validate required configuration and environment variables"""
    print("🔍 Validating configuration...")

    missing_vars = []
    for var in CORE_AWS_VARS:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing core AWS environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before running the setup.")
        return False

    # Validate LocalStack endpoint
    try:
        import requests

        response = requests.get(f"{LOCALSTACK_ENDPOINT}/_localstack/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ LocalStack health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to LocalStack: {e}")
        return False

    print("✅ Configuration validation passed")
    return True


def get_localstack_client(service_name: str):
    """Get a boto3 client configured for LocalStack with error handling"""
    try:
        client = boto3.client(
            service_name,
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        # Test the connection
        if service_name == "sts":
            client.get_caller_identity()
        return client
    except Exception as e:
        print(f"❌ Failed to create {service_name} client: {e}")
        raise


def wait_for_table_active(dynamodb_client, table_name: str, max_wait: int = 60):
    """Wait for DynamoDB table to become active"""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            if response["Table"]["TableStatus"] == "ACTIVE":
                return True
            time.sleep(1)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            time.sleep(1)
    return False


def create_dynamodb_tables():
    """Create all DynamoDB tables needed for the application"""
    print("📚 Creating DynamoDB tables...")
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
                {"AttributeName": "LKP", "AttributeType": "S"},
                {"AttributeName": "SRC_LANG", "AttributeType": "S"},
                {"AttributeName": "english_word", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "ReverseIndex",
                    "KeySchema": [
                        {"AttributeName": "LKP", "KeyType": "HASH"},
                        {"AttributeName": "SRC_LANG", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "EnglishWordIndex",
                    "KeySchema": [
                        {"AttributeName": "english_word", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
        {
            "TableName": "connectionsTable",
            "KeySchema": [{"AttributeName": "connectionId", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "connectionId", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "vocab_word", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "UserIndex",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "VocabWordConnectionsIndex",
                    "KeySchema": [
                        {"AttributeName": "vocab_word", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
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
            "AttributeDefinitions": [
                {"AttributeName": "listId", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "UserListIndex",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
        {
            "TableName": "vocabMediaTable",
            "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "english_word", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "EnglishWordMediaIndex",
                    "KeySchema": [
                        {"AttributeName": "english_word", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
    ]

    created_tables = []
    for table_config in tables:
        try:
            dynamodb.create_table(**table_config)
            print(f"✅ Created table: {table_config['TableName']}")
            created_tables.append(table_config["TableName"])

            # Wait for table to be active
            if wait_for_table_active(dynamodb, table_config["TableName"]):
                print(f"✅ Table {table_config['TableName']} is active")
            else:
                print(
                    f"⚠️  Table {table_config['TableName']} did not become active within timeout"
                )

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"⚠️  Table {table_config['TableName']} already exists")
                created_tables.append(table_config["TableName"])
            else:
                print(f"❌ Error creating table {table_config['TableName']}: {e}")
                raise

    return created_tables


def create_s3_bucket():
    """Create S3 bucket for media storage with enhanced configuration"""
    print("💾 Creating S3 bucket...")
    s3 = get_localstack_client("s3")

    bucket_name = os.getenv("S3_MEDIA_BUCKET_NAME", "vocab-media-bucket-local")

    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created S3 bucket: {bucket_name}")

        # Enable CORS for local development
        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "ExposeHeaders": ["ETag", "x-amz-meta-*"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }
        s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
        print(f"✅ Configured CORS for bucket: {bucket_name}")

        # Set up bucket policy for public read access (for development)
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                }
            ],
        }
        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(bucket_policy))
        print(f"✅ Set bucket policy for public read access: {bucket_name}")

        # Create test folder structure
        test_folders = ["audio/", "images/", "temp/"]
        for folder in test_folders:
            s3.put_object(Bucket=bucket_name, Key=folder, Body=b"")
        print(f"✅ Created folder structure in bucket: {bucket_name}")

    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyExists":
            print(f"⚠️  S3 bucket {bucket_name} already exists")
        else:
            print(f"❌ Error creating S3 bucket {bucket_name}: {e}")
            raise

    return bucket_name


def create_sqs_queues():
    """Create SQS queues for async processing"""
    print("📬 Creating SQS queues...")
    sqs = get_localstack_client("sqs")

    queues = [
        {
            "name": "vocab-processing-queue",
            "attributes": {
                "DelaySeconds": "0",
                "MessageRetentionPeriod": "1209600",  # 14 days
                "VisibilityTimeout": "300",
                "RedrivePolicy": json.dumps(
                    {
                        "deadLetterTargetArn": "arn:aws:sqs:us-east-1:000000000000:vocab-processing-dlq",
                        "maxReceiveCount": 3,
                    }
                ),
            },
        },
        {
            "name": "vocab-processing-dlq",
            "attributes": {
                "DelaySeconds": "0",
                "MessageRetentionPeriod": "1209600",  # 14 days
                "VisibilityTimeout": "300",
            },
        },
    ]

    created_queues = []
    for queue_config in queues:
        try:
            response = sqs.create_queue(
                QueueName=queue_config["name"], Attributes=queue_config["attributes"]
            )
            print(f"✅ Created SQS queue: {queue_config['name']}")
            print(f"   Queue URL: {response['QueueUrl']}")
            created_queues.append(response["QueueUrl"])

        except ClientError as e:
            if e.response["Error"]["Code"] == "QueueAlreadyExists":
                print(f"⚠️  SQS queue {queue_config['name']} already exists")
            else:
                print(f"❌ Error creating SQS queue {queue_config['name']}: {e}")
                raise

    return created_queues


def create_lambda_functions():
    """Create enhanced Lambda functions for WebSocket handling"""
    print("⚡ Creating Lambda functions...")
    lambda_client = get_localstack_client("lambda")

    # Enhanced WebSocket handler function
    function_code = """
import json
import boto3
import os
from datetime import datetime, timezone

def lambda_handler(event, context):
    connection_id = event.get('requestContext', {}).get('connectionId')
    route_key = event.get('requestContext', {}).get('routeKey')
    
    print(f"WebSocket event - Connection: {connection_id}, Route: {route_key}")
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', 
                             endpoint_url=os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566'))
    table = dynamodb.Table('connectionsTable')
    
    try:
        if route_key == '$connect':
            # Store connection info
            table.put_item(Item={
                'connectionId': connection_id,
                'connected_at': datetime.now(timezone.utc).isoformat(),
                'status': 'connected'
            })
            print(f"Connection {connection_id} stored")
            
        elif route_key == '$disconnect':
            # Remove connection
            table.delete_item(Key={'connectionId': connection_id})
            print(f"Connection {connection_id} removed")
            
        elif route_key == '$default':
            # Handle default route
            body = json.loads(event.get('body', '{}'))
            action = body.get('action', 'unknown')
            print(f"Default route - Action: {action}")
            
        return {'statusCode': 200, 'body': json.dumps('OK')}
        
    except Exception as e:
        print(f"Error handling WebSocket event: {e}")
        return {'statusCode': 500, 'body': json.dumps(f'Error: {str(e)}')}
"""

    # Create proper ZIP file for Lambda
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("lambda_function.py", function_code)
    zip_buffer.seek(0)

    functions = [
        {
            "FunctionName": "websocket-connect-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "lambda_function.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket connect handler for local testing",
            "Timeout": 30,
            "MemorySize": 128,
            "Environment": {
                "Variables": {
                    "AWS_ENDPOINT_URL": LOCALSTACK_ENDPOINT,
                    "DYNAMODB_CONNECTIONS_TABLE_NAME": "connectionsTable",
                }
            },
        },
        {
            "FunctionName": "websocket-disconnect-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "lambda_function.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket disconnect handler for local testing",
            "Timeout": 30,
            "MemorySize": 128,
            "Environment": {
                "Variables": {
                    "AWS_ENDPOINT_URL": LOCALSTACK_ENDPOINT,
                    "DYNAMODB_CONNECTIONS_TABLE_NAME": "connectionsTable",
                }
            },
        },
        {
            "FunctionName": "websocket-default-handler",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::000000000000:role/lambda-execution-role",
            "Handler": "lambda_function.lambda_handler",
            "Code": {"ZipFile": zip_buffer.getvalue()},
            "Description": "WebSocket default handler for local testing",
            "Timeout": 30,
            "MemorySize": 128,
            "Environment": {
                "Variables": {
                    "AWS_ENDPOINT_URL": LOCALSTACK_ENDPOINT,
                    "DYNAMODB_CONNECTIONS_TABLE_NAME": "connectionsTable",
                }
            },
        },
    ]

    created_functions = []
    for func_config in functions:
        try:
            response = lambda_client.create_function(**func_config)
            print(f"✅ Created Lambda function: {func_config['FunctionName']}")
            created_functions.append(response["FunctionArn"])

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceConflictException":
                print(
                    f"⚠️  Lambda function {func_config['FunctionName']} already exists"
                )
            else:
                print(
                    f"❌ Error creating Lambda function {func_config['FunctionName']}: {e}"
                )
                raise

    return created_functions


def create_iam_roles():
    """Create IAM roles with enhanced permissions"""
    print("🔑 Creating IAM roles...")
    iam = get_localstack_client("iam")

    roles = [
        {
            "RoleName": "lambda-execution-role",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "Description": "Lambda execution role for local testing",
            "Policies": [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
                "arn:aws:iam::aws:policy/AmazonS3FullAccess",
                "arn:aws:iam::aws:policy/AmazonSQSFullAccess",
            ],
        },
        {
            "RoleName": "apigateway-execution-role",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "apigateway.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "Description": "API Gateway execution role for local testing",
            "Policies": [
                "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
                "arn:aws:iam::aws:policy/AWSLambdaRole",
            ],
        },
    ]

    created_roles = []
    for role_config in roles:
        try:
            iam.create_role(
                RoleName=role_config["RoleName"],
                AssumeRolePolicyDocument=json.dumps(
                    role_config["AssumeRolePolicyDocument"]
                ),
                Description=role_config["Description"],
            )
            print(f"✅ Created IAM role: {role_config['RoleName']}")
            created_roles.append(role_config["RoleName"])

            # Attach policies
            for policy_arn in role_config["Policies"]:
                try:
                    iam.attach_role_policy(
                        RoleName=role_config["RoleName"],
                        PolicyArn=policy_arn,
                    )
                    print(
                        f"✅ Attached policy {policy_arn} to {role_config['RoleName']}"
                    )
                except ClientError as e:
                    print(f"⚠️  Policy {policy_arn} attachment failed: {e}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExistsException":
                print(f"⚠️  IAM role {role_config['RoleName']} already exists")
                created_roles.append(role_config["RoleName"])
            else:
                print(f"❌ Error creating IAM role {role_config['RoleName']}: {e}")
                raise

    return created_roles


def setup_local_environment():
    """Set up environment variables for local testing"""
    print("🔧 Setting up local environment...")

    env_vars = {
        "AWS_ENDPOINT_URL": LOCALSTACK_ENDPOINT,
        "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
        "AWS_DEFAULT_REGION": AWS_REGION,
        "DYNAMODB_VOCAB_TABLE_NAME": "vocabDataTable",
        "DYNAMODB_CONNECTIONS_TABLE_NAME": "connectionsTable",
        "DYNAMODB_VOCAB_MEDIA_TABLE_NAME": "vocabMediaTable",
        "S3_MEDIA_BUCKET_NAME": "vocab-media-bucket-local",
        "SQS_QUEUE_URL": "http://localhost:4566/000000000000/vocab-processing-queue",
        "WEBSOCKET_API_ENDPOINT": "ws://localhost:4566/",
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    print("✅ Local environment variables configured")
    return env_vars


def seed_test_data():
    """Seed test data for comprehensive testing"""
    print("🌱 Seeding test data...")

    dynamodb = boto3.resource("dynamodb", endpoint_url=LOCALSTACK_ENDPOINT)

    # Seed vocabulary data
    vocab_table = dynamodb.Table("vocabDataTable")
    vocab_items = [
        {
            "PK": "SRC#en#hello",
            "SK": "TGT#es#POS#noun",
            "source_word": "hello",
            "source_language": "en",
            "target_word": "hola",
            "target_language": "es",
            "source_definition": ["A greeting"],
            "source_pos": "noun",
            "target_pos": "noun",
            "LKP": "LKP#es#hola",
            "SRC_LANG": "SRC#en",
            "english_word": "hello",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "test_setup",
            "schema_version": 1,
        },
        {
            "PK": "SRC#en#house",
            "SK": "TGT#es#POS#noun",
            "source_word": "house",
            "source_language": "en",
            "target_word": "casa",
            "target_language": "es",
            "source_definition": ["A building where people live"],
            "source_pos": "noun",
            "target_pos": "feminine noun",
            "target_article": "la",
            "LKP": "LKP#es#casa",
            "SRC_LANG": "SRC#en",
            "english_word": "house",
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "test_setup",
            "schema_version": 1,
        },
    ]

    for item in vocab_items:
        vocab_table.put_item(Item=item)

    print(f"✅ Seeded {len(vocab_items)} vocabulary items")

    # Seed connection data
    connections_table = dynamodb.Table("connectionsTable")
    connection_items = [
        {
            "connectionId": "test-connection-1",
            "user_id": "test-user-1",
            "connected_at": "2024-01-01T00:00:00Z",
            "status": "connected",
        },
        {
            "connectionId": "test-connection-2",
            "user_id": "test-user-2",
            "connected_at": "2024-01-01T00:00:00Z",
            "status": "connected",
        },
    ]

    for item in connection_items:
        connections_table.put_item(Item=item)

    print(f"✅ Seeded {len(connection_items)} connection items")


def verify_setup():
    """Verify that all resources were created successfully"""
    print("🔍 Verifying setup...")

    verification_results = {}

    # Check DynamoDB tables
    try:
        dynamodb = get_localstack_client("dynamodb")
        tables = dynamodb.list_tables()
        verification_results["dynamodb_tables"] = tables["TableNames"]
        print(f"✅ DynamoDB tables verified: {len(tables['TableNames'])} tables")
    except Exception as e:
        verification_results["dynamodb_tables"] = f"Error: {e}"
        print(f"❌ DynamoDB verification failed: {e}")

    # Check S3 buckets
    try:
        s3 = get_localstack_client("s3")
        buckets = s3.list_buckets()
        verification_results["s3_buckets"] = [b["Name"] for b in buckets["Buckets"]]
        print(f"✅ S3 buckets verified: {len(buckets['Buckets'])} buckets")
    except Exception as e:
        verification_results["s3_buckets"] = f"Error: {e}"
        print(f"❌ S3 verification failed: {e}")

    # Check SQS queues
    try:
        sqs = get_localstack_client("sqs")
        queues = sqs.list_queues()
        verification_results["sqs_queues"] = queues.get("QueueUrls", [])
        print(f"✅ SQS queues verified: {len(queues.get('QueueUrls', []))} queues")
    except Exception as e:
        verification_results["sqs_queues"] = f"Error: {e}"
        print(f"❌ SQS verification failed: {e}")

    # Check Lambda functions
    try:
        lambda_client = get_localstack_client("lambda")
        functions = lambda_client.list_functions()
        verification_results["lambda_functions"] = [
            f["FunctionName"] for f in functions["Functions"]
        ]
        print(f"✅ Lambda functions verified: {len(functions['Functions'])} functions")
    except Exception as e:
        verification_results["lambda_functions"] = f"Error: {e}"
        print(f"❌ Lambda verification failed: {e}")

    return verification_results


def main():
    """Enhanced main setup function"""
    print("🚀 Starting Enhanced LocalStack AWS Setup...")
    print("=" * 70)

    # Set up environment first
    setup_local_environment()

    # Validate configuration
    if not validate_configuration():
        print("❌ Configuration validation failed. Exiting.")
        sys.exit(1)

    try:
        # Create resources
        print("\n📚 Creating DynamoDB tables...")
        tables = create_dynamodb_tables()

        print("\n💾 Creating S3 buckets...")
        bucket = create_s3_bucket()

        print("\n📬 Creating SQS queues...")
        queues = create_sqs_queues()

        print("\n🔑 Creating IAM roles...")
        roles = create_iam_roles()

        print("\n⚡ Creating Lambda functions...")
        functions = create_lambda_functions()

        print("\n🌱 Seeding test data...")
        seed_test_data()

        print("\n🔍 Verifying setup...")
        verify_setup()

        # Print comprehensive summary
        print("\n" + "=" * 70)
        print("✅ Enhanced LocalStack Setup Complete!")
        print(f"🌐 LocalStack Endpoint: {LOCALSTACK_ENDPOINT}")
        print(f"📊 DynamoDB Tables: {len(tables)}")
        print(f"💾 S3 Buckets: 1 ({bucket})")
        print(f"📬 SQS Queues: {len(queues)}")
        print(f"🔑 IAM Roles: {len(roles)}")
        print(f"⚡ Lambda Functions: {len(functions)}")

        print("\n🧪 Ready for comprehensive end-to-end testing!")
        print("\nNext steps:")
        print("  python test_comprehensive_e2e.py  # Run comprehensive tests")
        print("  python test_localstack_simple.py  # Run simple tests")
        print(
            "  curl http://localhost:4566/_localstack/health  # Check LocalStack health"
        )

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error above and retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()

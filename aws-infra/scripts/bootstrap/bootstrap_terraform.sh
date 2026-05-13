#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Bootstrap Terraform backend + role:
  - S3 bucket for state
  - DynamoDB table for state locking
  - IAM role to assume for Terraform

Prereqs:
  - AWS CLI v2 configured (uses --profile if provided)

Examples:
  scripts/bootstrap/bootstrap_terraform.sh \
    --region us-east-1 \
    --profile personal \
    --bucket wordweave-terraform-state-123456789012 \
    --dynamodb-table wordweave-terraform-locks \
    --role-name wordweave-terraform \
    --write-backend-config

Options:
  --region <region>                 AWS region
  --profile <profile>               AWS profile used as source creds (optional)
  --bucket <bucket>                 S3 bucket name for TF state
  --dynamodb-table <table>          DynamoDB table name for TF locks
  --role-name <name>                IAM role name to create/use
  --trust-arn <arn>                 Principal ARN allowed to assume the role (default: current caller ARN)
  --write-backend-config            Write backend.hcl for common/dev (NOT committed)
  --help                            Show help
EOF
}

REGION="us-east-1"
PROFILE=""
BUCKET=""
LOCK_TABLE=""
ROLE_NAME="wordweave-terraform"
TRUST_ARN=""
WRITE_BACKEND_CONFIG="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --bucket) BUCKET="$2"; shift 2 ;;
    --dynamodb-table) LOCK_TABLE="$2"; shift 2 ;;
    --role-name) ROLE_NAME="$2"; shift 2 ;;
    --trust-arn) TRUST_ARN="$2"; shift 2 ;;
    --write-backend-config) WRITE_BACKEND_CONFIG="true"; shift 1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

aws_cli=(aws)
if [[ -n "${PROFILE}" ]]; then
  aws_cli+=(--profile "${PROFILE}")
fi
aws_cli+=(--region "${REGION}")

account_id="$("${aws_cli[@]}" sts get-caller-identity --query Account --output text)"
caller_arn="$("${aws_cli[@]}" sts get-caller-identity --query Arn --output text)"

if [[ -z "${BUCKET}" ]]; then
  BUCKET="wordweave-terraform-state-${account_id}"
fi
if [[ -z "${LOCK_TABLE}" ]]; then
  LOCK_TABLE="wordweave-terraform-locks"
fi
if [[ -z "${TRUST_ARN}" ]]; then
  TRUST_ARN="${caller_arn}"
fi

echo "Region:        ${REGION}"
echo "Account:       ${account_id}"
echo "Profile:       ${PROFILE:-<default>}"
echo "State bucket:  ${BUCKET}"
echo "Lock table:    ${LOCK_TABLE}"
echo "Role name:     ${ROLE_NAME}"
echo "Trust ARN:     ${TRUST_ARN}"
echo

ensure_bucket() {
  if "${aws_cli[@]}" s3api head-bucket --bucket "${BUCKET}" >/dev/null 2>&1; then
    echo "S3 bucket exists: ${BUCKET}"
    return 0
  fi

echo "Creating S3 bucket: ${BUCKET}"
  if [[ "${REGION}" == "us-east-1" ]]; then
    "${aws_cli[@]}" s3api create-bucket --bucket "${BUCKET}" >/dev/null
  else
    "${aws_cli[@]}" s3api create-bucket \
      --bucket "${BUCKET}" \
      --create-bucket-configuration LocationConstraint="${REGION}" >/dev/null
  fi

  "${aws_cli[@]}" s3api put-bucket-versioning \
    --bucket "${BUCKET}" \
    --versioning-configuration Status=Enabled >/dev/null

  "${aws_cli[@]}" s3api put-bucket-encryption \
    --bucket "${BUCKET}" \
    --server-side-encryption-configuration '{
      "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }' >/dev/null

  "${aws_cli[@]}" s3api put-public-access-block \
    --bucket "${BUCKET}" \
    --public-access-block-configuration '{
      "BlockPublicAcls": true,
      "IgnorePublicAcls": true,
      "BlockPublicPolicy": true,
      "RestrictPublicBuckets": true
    }' >/dev/null
}

ensure_lock_table() {
  if "${aws_cli[@]}" dynamodb describe-table --table-name "${LOCK_TABLE}" >/dev/null 2>&1; then
    echo "DynamoDB table exists: ${LOCK_TABLE}"
    return 0
  fi

  echo "Creating DynamoDB lock table: ${LOCK_TABLE}"
  "${aws_cli[@]}" dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST >/dev/null

  "${aws_cli[@]}" dynamodb wait table-exists --table-name "${LOCK_TABLE}"
}

ensure_role() {
  role_arn="$("${aws_cli[@]}" iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text 2>/dev/null || true)"
  if [[ -n "${role_arn}" && "${role_arn}" != "None" ]]; then
    echo "IAM role exists: ${role_arn}"
    echo "${role_arn}"
    return 0
  fi

  echo "Creating IAM role: ${ROLE_NAME}"
  trust_policy="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "${TRUST_ARN}" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)"

  "${aws_cli[@]}" iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "${trust_policy}" >/dev/null

  "${aws_cli[@]}" iam attach-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess >/dev/null

  role_arn="$("${aws_cli[@]}" iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)"
  echo "Created role: ${role_arn}"
  echo "${role_arn}"
}

write_backend_hcl() {
  local env_dir="$1"
  local key="$2"
  local role_arn="$3"
  local out="${env_dir}/backend.hcl"

  cat > "${out}" <<EOF
bucket         = "${BUCKET}"
key            = "${key}"
region         = "${REGION}"
dynamodb_table = "${LOCK_TABLE}"
encrypt        = true
role_arn       = "${role_arn}"
EOF
  echo "Wrote ${out}"
}

ensure_bucket
ensure_lock_table
role_arn="$(ensure_role)"

echo
echo "Terraform role ARN:"
echo "  ${role_arn}"

if [[ "${WRITE_BACKEND_CONFIG}" == "true" ]]; then
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  write_backend_hcl "${repo_root}/environments/common" "common/terraform.tfstate" "${role_arn}"
  write_backend_hcl "${repo_root}/environments/dev" "dev/terraform.tfstate" "${role_arn}"
fi


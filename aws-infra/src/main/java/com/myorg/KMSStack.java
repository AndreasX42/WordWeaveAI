// package com.myorg;

// import software.amazon.awscdk.services.kms.Key;
// import software.amazon.awscdk.RemovalPolicy;
// import software.constructs.Construct;
// import software.amazon.awscdk.Stack;
// import software.amazon.awscdk.StackProps;
// import software.amazon.awscdk.services.iam.IGrantable;

// public class KMSStack extends Stack {

// private final Key cmk;

// public Key getCmk() {
// return cmk;
// }

// public KMSStack(final Construct scope, final String id) {
// this(scope, id, null);
// }

// public KMSStack(final Construct scope, final String id, final StackProps
// props) {
// super(scope, id, props);

// this.cmk = Key.Builder.create(this, "cmk")
// .description("CMK for secrets")
// .enableKeyRotation(true)
// .removalPolicy(RemovalPolicy.DESTROY)
// .build();
// }

// public void grantDecrypt(IGrantable grantee) {
// cmk.grantDecrypt(grantee);
// }

// }

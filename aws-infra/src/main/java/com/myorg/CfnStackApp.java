package com.myorg;

import java.util.Optional;

import io.github.cdimascio.dotenv.Dotenv;
import software.amazon.awscdk.App;
import software.amazon.awscdk.Environment;
import software.amazon.awscdk.StackProps;

public class CfnStackApp {

	private static Dotenv dotenv;

	public static void main(final String[] args) {

		dotenv = Dotenv.configure().ignoreIfMissing().load();
		String account = getRequiredVariable("CDK_DEFAULT_ACCOUNT");
		String region = getRequiredVariable("CDK_DEFAULT_REGION");

		App app = new App();

		new VocabStack(app, "vStack", StackProps.builder()
				.env(Environment.builder()
						.account(account)
						.region(region)
						.build())
				.build());

		app.synth();
	}

	// Public static getter for other classes to access required variables
	public static String getRequiredVariable(String varName) {
		return Optional.ofNullable(dotenv.get(varName))
				.or(() -> Optional.ofNullable(System.getenv(varName)))
				.orElseThrow(() -> new RuntimeException(
						"Missing required configuration variable: " + varName));
	}
}

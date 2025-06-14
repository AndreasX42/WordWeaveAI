package com.myorg;

import java.util.List;

import software.amazon.awscdk.RemovalPolicy;
import software.amazon.awscdk.Stack;
import software.amazon.awscdk.StackProps;
import software.amazon.awscdk.services.certificatemanager.Certificate;
import software.amazon.awscdk.services.certificatemanager.CertificateValidation;
import software.amazon.awscdk.services.certificatemanager.ICertificate;
import software.amazon.awscdk.services.ec2.ISecurityGroup;
import software.amazon.awscdk.services.ec2.IVpc;
import software.amazon.awscdk.services.ec2.Peer;
import software.amazon.awscdk.services.ec2.Port;
import software.amazon.awscdk.services.ec2.SecurityGroup;
import software.amazon.awscdk.services.ec2.SubnetSelection;
import software.amazon.awscdk.services.ec2.SubnetType;
import software.amazon.awscdk.services.elasticloadbalancingv2.ApplicationLoadBalancer;
import software.amazon.awscdk.services.elasticloadbalancingv2.ApplicationProtocol;
import software.amazon.awscdk.services.elasticloadbalancingv2.BaseApplicationListenerProps;
import software.amazon.awscdk.services.elasticloadbalancingv2.FixedResponseOptions;
import software.amazon.awscdk.services.elasticloadbalancingv2.IApplicationListener;
import software.amazon.awscdk.services.elasticloadbalancingv2.IApplicationLoadBalancer;
import software.amazon.awscdk.services.elasticloadbalancingv2.ListenerAction;
import software.amazon.awscdk.services.elasticloadbalancingv2.ListenerCertificate;
import software.amazon.awscdk.services.elasticloadbalancingv2.RedirectOptions;
import software.amazon.awscdk.services.route53.ARecord;
import software.amazon.awscdk.services.route53.HostedZone;
import software.amazon.awscdk.services.route53.HostedZoneProviderProps;
import software.amazon.awscdk.services.route53.IHostedZone;
import software.amazon.awscdk.services.route53.RecordTarget;
import software.amazon.awscdk.services.route53.targets.LoadBalancerTarget;
import software.constructs.Construct;

public class ALBStack extends Stack {

	private final IApplicationListener httpsListener;
	private final ISecurityGroup albSecurityGroup;
	private final IApplicationLoadBalancer loadBalancer;

	private final String frontendDomainName = CfnStackApp.getRequiredVariable("FRONTEND_DOMAIN_NAME");
	private final String backendDomainName = CfnStackApp.getRequiredVariable("BACKEND_DOMAIN_NAME");

	public ALBStack(final Construct scope, final String id, final StackProps props, final IVpc vpc) {
		super(scope, id, props);

		// ALB Security Group
		this.albSecurityGroup = SecurityGroup.Builder.create(this, "AlbSg")
				.vpc(vpc)
				.description("SG for ALB")
				.allowAllOutbound(true)
				.build();

		// Allow inbound traffic on ports 80 and 443 from anywhere
		this.albSecurityGroup.addIngressRule(Peer.anyIpv4(), Port.tcp(80), "Allow http inbound");
		this.albSecurityGroup.addIngressRule(Peer.anyIpv4(), Port.tcp(443),
				"Allow https inbound");

		// Application Load Balancer
		this.loadBalancer = ApplicationLoadBalancer.Builder.create(this, "vAlb")
				.vpc(vpc)
				.internetFacing(true)
				.securityGroup(this.albSecurityGroup)
				.vpcSubnets(SubnetSelection.builder().subnetType(SubnetType.PUBLIC).build())
				.build();

		// HTTP Listener (Port 80) - Redirects to HTTPS
		loadBalancer.addListener("HttpListener",
				BaseApplicationListenerProps.builder()
						.port(80)
						.protocol(ApplicationProtocol.HTTP)
						.defaultAction(ListenerAction.redirect(RedirectOptions.builder()
								.protocol("HTTPS")
								.port("443")
								.permanent(true)
								.build()))
						.build());

		// HTTPS Listener (Port 443)
		// Try to get certificate ARN from context, otherwise create a new one
		String certificateArn = CfnStackApp.getRequiredVariable("ACM_CERTIFICATE_ARN");
		ICertificate certificate;

		if (certificateArn != null && !certificateArn.isEmpty()) {
			certificate = Certificate.fromCertificateArn(this, "AlbCertificate", certificateArn);
		} else {
			certificate = Certificate.Builder.create(this, "AlbCertificate")
					.domainName(getFrontendDomainName())
					.subjectAlternativeNames(List.of(getBackendDomainName()))
					.validation(CertificateValidation.fromDns())
					.build();

			// Apply removal policy only if the certificate is created by this stack
			certificate.applyRemovalPolicy(RemovalPolicy.RETAIN);
		}

		// retain certificate, but destroy alb and sg if stack is deleted
		loadBalancer.applyRemovalPolicy(RemovalPolicy.DESTROY);
		albSecurityGroup.applyRemovalPolicy(RemovalPolicy.DESTROY);

		this.httpsListener = loadBalancer.addListener("HttpsListener", BaseApplicationListenerProps.builder()
				.port(443)
				.protocol(ApplicationProtocol.HTTPS)
				.certificates(List.of(ListenerCertificate.fromCertificateManager(certificate)))
				.defaultAction(ListenerAction.fixedResponse(400, FixedResponseOptions.builder()
						.contentType("application/json")
						.messageBody("{\"error\": \"Resource not found\"}")
						.build()))
				.build());

		// --- Route 53 Integration ---

		// 1. Look up the hosted zone in Route 53
		IHostedZone hostedZone = HostedZone.fromLookup(this, "HostedZone", HostedZoneProviderProps.builder()
				.domainName(getFrontendDomainName())
				.build());

		// 2. Create Alias records pointing to the ALB
		// Alias record for the apex domain (e.g., quizstreams.com)
		ARecord.Builder.create(this, "ApexAliasRecord")
				.zone(hostedZone)
				.recordName(getFrontendDomainName())
				.target(RecordTarget.fromAlias(new LoadBalancerTarget(this.loadBalancer)))
				.build();

		// Alias record for the subdomain (e.g., api.quizstreams.com)
		ARecord.Builder.create(this, "ApiAliasRecord")
				.zone(hostedZone)
				.recordName(getBackendDomainName())
				.target(RecordTarget.fromAlias(new LoadBalancerTarget(this.loadBalancer)))
				.build();
	}

	// Getters for other stacks to use
	public IApplicationListener getHttpsListener() {
		return httpsListener;
	}

	public ISecurityGroup getAlbSecurityGroup() {
		return albSecurityGroup;
	}

	public IApplicationLoadBalancer getLoadBalancer() {
		return loadBalancer;
	}

	public String getFrontendDomainName() {
		return frontendDomainName;
	}

	public String getBackendDomainName() {
		return backendDomainName;
	}
}
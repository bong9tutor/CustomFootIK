// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class CustomFootIK : ModuleRules
{
	public CustomFootIK(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"CustomFootIK",
			"CustomFootIK/Variant_Platforming",
			"CustomFootIK/Variant_Platforming/Animation",
			"CustomFootIK/Variant_Combat",
			"CustomFootIK/Variant_Combat/AI",
			"CustomFootIK/Variant_Combat/Animation",
			"CustomFootIK/Variant_Combat/Gameplay",
			"CustomFootIK/Variant_Combat/Interfaces",
			"CustomFootIK/Variant_Combat/UI",
			"CustomFootIK/Variant_SideScrolling",
			"CustomFootIK/Variant_SideScrolling/AI",
			"CustomFootIK/Variant_SideScrolling/Gameplay",
			"CustomFootIK/Variant_SideScrolling/Interfaces",
			"CustomFootIK/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}

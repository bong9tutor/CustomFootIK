# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Unreal Engine 5.7 기반의 **학습용 프로젝트**입니다. IK Rig와 Control Rig를 사용해 캐릭터의 **Foot Placement(발 배치)** 를 구현하는 것이 목적입니다. UE 기본 ThirdPerson 템플릿에서 출발하되, 발이 지면(경사면, 계단 등)에 자연스럽게 정합되도록 커스텀 Foot IK 로직을 ABP/Control Rig 레벨에서 학습·구축하는 것이 주된 작업 영역입니다.

C++ 모듈명은 `CustomFootIK` (Runtime). 게임 로직 자체는 단순하며, **본 프로젝트의 학습 가치는 대부분 Content 측 에셋(애님 블루프린트, IK Rig, Control Rig)** 에 있습니다.

## 핵심 구조

### 진입점 / 부트스트랩
- **기본 맵**: `Content/CustomFootIK/L_StartMap.umap` (`Config/DefaultEngine.ini`의 `GameDefaultMap` / `EditorStartupMap` 둘 다 이 맵).
- **기본 GameMode**: `Content/ThirdPerson/Blueprints/BP_ThirdPersonGameMode` (DefaultEngine.ini의 `GlobalDefaultGameMode`). C++ `ACustomFootIKGameMode`는 현재 빈 stub이며, 실제 Pawn/Controller 지정은 BP 측에서 이뤄집니다.
- **C++ 캐릭터 클래스 `ACustomFootIKCharacter`** (`Source/CustomFootIK/CustomFootIKCharacter.h`): `abstract`. SpringArm + FollowCamera + EnhancedInput 액션(Move/Look/Jump/MouseLook) 만 정의. Blueprint(`BP_Mage`, `BP_ThirdPersonCharacter`)에서 상속하여 사용.

### Foot IK 학습 대상 (가장 중요한 디렉터리)
- `Content/Characters/Mage/Rigs/IK_Mage.uasset` — **IK Rig 에셋** (체인/타깃 정의).
- `Content/Characters/Mage/Rigs/CR_Mage_FootIK.uasset` — **Control Rig 에셋** (Foot IK 로직 본체). 발 trace, 지면 노멀, 골반 보정 등의 그래프가 여기에 들어갑니다.
- `Content/CustomFootIK/ABP_Mage.uasset` — **Anim Blueprint**. AnimGraph에서 위 Control Rig 노드를 호출해 최종 포즈를 합성하는 지점.
- `Content/CustomFootIK/BP_Mage.uasset` — 위 ABP/스켈레탈 메시를 사용하는 캐릭터 Blueprint.
- `Content/Characters/Mage/SkeletalMeshes/Mage_Skeleton.uasset` — 위 모든 Rig가 의존하는 스켈레톤.

수정 작업은 거의 항상 위 5개 에셋 사이에서 이뤄지며, C++ 변경이 필요한 경우는 드뭅니다.

### C++ 모듈 (`Source/CustomFootIK/`)
파일 5쌍 (`CustomFootIK`, `CustomFootIKCharacter`, `CustomFootIKGameMode`, `CustomFootIKPlayerController` 그리고 `.Build.cs`). 클래스들은 모두 `abstract` 또는 stub 수준이며 게임플레이 로직은 거의 없음. `CustomFootIK.Build.cs`의 의존성에 `EnhancedInput`, `AIModule`, `StateTreeModule`, `GameplayStateTreeModule`, `UMG`, `Slate` 가 포함되어 있는데, 현재 코드에서 실제로 사용되는 것은 EnhancedInput 정도입니다. StateTree류는 활성화된 플러그인과 묶인 잔재.

### 활성 플러그인
`StateTree`, `GameplayStateTree`, `ModelingToolsEditorMode` (Editor only), `Monolith` (Editor MCP 서버 — 아래 MCP 활용 참고). 추가로 `Plugins/Developer/RiderLink`는 .gitignore에 의해 무시됨.

## MCP 활용 (적극 권장)

본 프로젝트는 **두 개의 MCP 서버를 적극적으로 활용**하도록 설정되어 있습니다. 단순한 grep/Read보다 MCP가 훨씬 정확한 경우가 많으니 **우선 사용**하세요.

### Monolith MCP (`mcp__monolith__*`) — UE 에디터 직결

`Plugins/Monolith` 플러그인이 UE 에디터 안에서 HTTP 서버(포트 9316)를 띄우고, `.mcp.json` (Python 프록시 경유)이 Claude Code와 연결합니다. **에디터가 켜져 있어야** 도구가 활성화됩니다.

도구 등록 방식: 도메인별 단일 `{namespace}_query(action, params)` 호출. 어떤 액션이 있는지 모를 때는 `monolith_discover()` / `monolith_guide()` 로 자동 색인을 받아오면 됩니다.

본 프로젝트에서 특히 중요한 네임스페이스:
- **`blueprint_query`** — `BP_Mage`, `BP_ThirdPersonCharacter` 등 블루프린트 그래프/변수/노드 인스펙션과 수정. Read로는 .uasset 바이너리를 못 읽으므로 **블루프린트 분석은 Monolith가 사실상 유일한 수단**.
- **`animation_query`** — `ABP_Mage`의 AnimGraph, State Machine, 본 Foot IK가 호출되는 Control Rig 노드 위치 파악.
- **`material_query`**, **`mesh_query`** — Mage 머티리얼/스켈레탈 메시 점검.
- **`source_query`** — UE 5.7 엔진 소스 1M+ 심볼 오프라인 검색. `FAnimNode_ControlRig`, `UIKRigDefinition`, `Foot IK` 관련 엔진 측 구현을 찾을 때 유용.
- **`config_query`** — `DefaultEngine.ini` 등 ini 안전 편집.

`.uasset` 관련 작업이 들어오면 **항상 Monolith를 먼저 시도**하세요. (Read로 파일을 열어 LFS 포인터만 보이는 케이스 방지)

### JetBrains MCP (`mcp__jetbrains__*`) — Rider 통합

Rider IDE에 직결되어 C++ 측 모든 작업이 가능합니다. 본 프로젝트는 `Plugins/Developer/RiderLink`로 Rider를 1차 IDE로 사용하는 것을 가정합니다.

자주 쓸 도구:
- **`mcp__jetbrains__search_symbol` / `get_symbol_info`** — UE 엔진까지 포함한 심볼 점프. C++ grep보다 정확.
- **`mcp__jetbrains__search_in_files_by_regex` / `search_in_files_by_text`** — 솔루션 범위 검색. 외부 인덱스 사용해 빠름.
- **`mcp__jetbrains__get_file_problems`** — 컴파일/인스펙션 오류 즉시 확인 (UE 코드 변경 후 검증용).
- **`mcp__jetbrains__build_solution`** / **`execute_run_configuration`** — 빌드·실행 (별도 UBT 명령 불필요).
- **`mcp__jetbrains__open_file_in_editor`** — 작업 중인 위치를 사용자에게 시각적으로 노출.
- **`mcp__jetbrains__rename_refactoring`** — C++ 심볼 안전 리네임 (수동 sed 금지).

**도구 선택 규칙**: 일반 파일 작업은 Read/Edit, C++/솔루션 차원은 JetBrains MCP, `.uasset`/Blueprint/Animation/Material 차원은 Monolith MCP 우선.

## Git / 에셋 관리

- **Git LFS 필수**: `.gitattributes`가 `*.uasset`, `*.umap`을 LFS로 추적합니다. 클론/풀 전에 `git lfs install` 이 필요.
- **이진 에셋은 머지 불가**: Blueprint/Control Rig/ABP 같은 `.uasset` 충돌은 git으로 해결할 수 없습니다. 같은 에셋을 동시에 편집하지 마세요.
- **커밋 단위**: 학습 단계별로 한 단계 = 한 커밋을 지향. 과거 사용하지 않는 템플릿(Variant_*)을 정리한 사례가 이미 있으므로, 의미 있는 단계 외의 자잘한 추가/삭제가 누적되지 않도록 정리해 가며 진행.

## 작업 시 참고

- 게임을 "동작시켜 확인" 해야 한다고 보고할 일이 생기면, 자동 테스트는 없습니다. 에디터에서 PIE 로 직접 확인하거나, 사용자에게 결과 확인을 요청하세요.
- 새 캐릭터/맵을 추가할 때 `DefaultEngine.ini`의 redirect 섹션(`ActiveGameNameRedirects`, `ActiveClassRedirects`) 은 과거 ThirdPerson 템플릿에서 리네임한 흔적이므로 함부로 지우지 마세요. 기존 에셋 참조가 깨질 수 있습니다.

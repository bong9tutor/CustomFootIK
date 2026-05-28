# Foot Placement — Implementation Reference

> **이 문서의 위치 (Diataxis: reference)**
> - 학습은 `FootPlacement_Learning.md` 로
> - 결함·해결책·확장 과제는 `FootPlacement_Troubleshooting.md` 로
> - 본 문서는 **Monolith MCP 로 직접 측정한 구현 사실의 단일 진실 공급원(SSOT)** 이다. 평가/제안 없이 측정값과 노드/핀/링크/파라미터만 담는다.
>
> 분석 대상
> - `Content/CustomFootIK/ABP_Mage.uasset` (Anim Blueprint)
> - `Content/Characters/Mage/Rigs/CR_Mage_FootIK.uasset` (Control Rig)
> - `Content/Characters/Mage/Rigs/IK_Mage.uasset` (IK Rig)
> - 의존 에셋: `Mage_Skeleton`, `Mage` (Skeletal Mesh), `Idle_B` (Animation Sequence)
>
> 분석 도구: Monolith MCP (`animation_query`, `blueprint_query`) — UE 5.7.0 / Monolith v0.16.0
> 최초 작성: 2026-05-28 / 최신 갱신: 2026-05-28

---

## 1. 에셋·코드 의존 관계

```
ACustomFootIKCharacter (C++, abstract)
        ▲
        │  Blueprint 상속
BP_Mage (Content/CustomFootIK)
        ├─ 블루프린트 자체 컴포넌트: 0
        └─ 상속 네이티브 컴포넌트 6
              ├─ CollisionCylinder  (UCapsuleComponent, root)
              ├─ Arrow              (UArrowComponent,   parent=CollisionCylinder)
              ├─ CharMoveComp       (UCharacterMovementComponent)
              ├─ CharacterMesh0     (USkeletalMeshComponent, parent=CollisionCylinder)
              │     ├─ SkeletalMesh: Mage
              │     └─ AnimClass:    ABP_Mage
              │                          ├─ Skeleton:    Mage_Skeleton    ← 가상 본 3개 포함
              │                          ├─ AnimGraph:   §3 참고
              │                          ├─ EventGraph:  §4 참고 (현재 데드)
              │                          ├─ Control Rig: CR_Mage_FootIK   (§6)
              │                          └─ Variables:   FootLOffset, FootROffset (Vector, 미사용)
              ├─ CameraBoom         (USpringArmComponent, parent=CollisionCylinder)
              └─ FollowCamera       (UCameraComponent,    parent=CameraBoom)
```

C++ 캐릭터(`ACustomFootIKCharacter`) 는 카메라·입력만 다루며 **Foot IK 관련 데이터를 ABP 에 푸시하는 경로가 없다.**

---

## 2. Mage_Skeleton

| 항목       | 값                                       |
|------------|------------------------------------------|
| 실제 본    | 23                                       |
| 가상 본    | 3                                        |
| 합계       | 26                                       |

### 2.1 가상 본 (Virtual Bones)

| 이름           | source         | target   |
|----------------|----------------|----------|
| `VB Foot_Root` | `root`         | `root`   |
| `VB Foot_R`    | `VB Foot_Root` | `foot_r` |
| `VB Foot_L`    | `VB Foot_Root` | `foot_l` |

가상 본 의미·도입 이유는 `FootPlacement_Learning.md` §3 참고. 본 문서는 “3 개가 존재한다” 까지만 사실로 기록.

---

## 3. ABP_Mage — AnimGraph

### 3.1 기본 정보

| 항목               | 값                                                  |
|--------------------|-----------------------------------------------------|
| Skeleton           | `Mage_Skeleton`                                     |
| Parent Class       | `AnimInstance`                                      |
| Graph 수           | 2 (`AnimGraph`, `EventGraph`)                       |
| Variable 수        | 2 (`FootLOffset:Vector`, `FootROffset:Vector`)      |
| State Machine 수   | 0                                                   |
| Sequence 의존      | `Idle_B`                                            |

### 3.2 AnimGraph 노드

`blueprint_query / get_graph_data` 기준으로 **전체 6 노드**. 평가되는 pose 경로(3 노드)와 미평가 확장 경로(3 노드)로 구분된다.

| 구분            | 노드                          | 클래스                         |
|-----------------|-------------------------------|--------------------------------|
| 활성 pose 경로  | `AnimGraphNode_SequencePlayer_0` (`Idle_B`) | `AnimGraphNode_SequencePlayer` |
| 활성 pose 경로  | `AnimGraphNode_ControlRig_0`               | `AnimGraphNode_ControlRig`     |
| 활성 pose 경로  | `AnimGraphNode_Root_0` (`Output Pose`)     | `AnimGraphNode_Root`           |
| 비활성 확장     | `AnimGraphNode_IKRig_0`                    | `AnimGraphNode_IKRig`          |
| 비활성 확장     | `K2Node_VariableGet_0` (`Get FootROffset`) | `K2Node_VariableGet`           |
| 비활성 확장     | `K2Node_VariableGet_1` (`Get FootLOffset`) | `K2Node_VariableGet`           |

### 3.3 활성 pose 경로 연결

```
SequencePlayer(Idle_B).Pose ──► ControlRig.Source
                              (ControlRig.Pose) ──► Root.Result
```

`ControlRig` 노드 핀:
| 핀               | 방향   | 값/연결                       |
|------------------|--------|-------------------------------|
| `Source`         | input  | `SequencePlayer.Pose`         |
| `Alpha`          | input  | `1.000000` (상수)             |
| `ShouldDoIKTrace`| input  | `true` (상수, 미연결)         |
| `Pose`           | output | `Root.Result`                 |

### 3.4 비활성 확장 경로 연결

```
                       (Source/Pose 미연결 — 이 노드는 평가되지 않음)
IKRig.Source     ─ 미연결
IKRig.Pose       ─ 미연결
IKRig.Alpha      = 1.000000 (상수)
IKRig.Position_foot_r_Goal       ◄── (Get) FootROffset
IKRig.PositionAlpha_foot_r_Goal  = 1.0
IKRig.Position_foot_l_Goal       ◄── (Get) FootLOffset
IKRig.PositionAlpha_foot_l_Goal  = 1.0
```

`IKRig` 노드의 IK Rig 에셋 참조는 `IK_Mage` (§7).

### 3.5 변수

| 이름           | 타입   | 기본값 | 사용 위치                                                          |
|----------------|--------|--------|--------------------------------------------------------------------|
| `FootLOffset`  | Vector | (0,0,0) | AnimGraph: `IKRig.Position_foot_l_Goal` / EventGraph: 5개의 Setter (§4) |
| `FootROffset`  | Vector | (0,0,0) | AnimGraph: `IKRig.Position_foot_r_Goal` / EventGraph: 5개의 Setter (§4) |

---

## 4. ABP_Mage — EventGraph (현재 미실행)

> **사실 정정 메모** — 이 그래프는 “비어 있지 않다”. **10 개 노드** 가 존재하며, `BlueprintUpdateAnimation` 의 `then` 실행 핀이 `Branch.execute` 에 **연결되지 않아 전체 체인이 런타임에서 실행되지 않을 뿐**이다.

### 4.1 노드 (총 10)

| ID                       | 클래스                  | 제목/함수                                          |
|--------------------------|-------------------------|----------------------------------------------------|
| `K2Node_Event_0`         | `K2Node_Event`          | `Event Blueprint Update Animation`                 |
| `K2Node_CallFunction_5`  | `K2Node_CallFunction`   | `Try Get Pawn Owner` (Target: AnimInstance)        |
| `K2Node_CallFunction_1`  | `K2Node_CallFunction`   | `Get Movement Component` (Target: Pawn)            |
| `K2Node_CallFunction_2`  | `K2Node_CallFunction`   | `Is Falling` (Target: NavMovementInterface)        |
| `K2Node_CallFunction_3`  | `K2Node_CallFunction`   | `NOT Boolean` (`KismetMathLibrary::Not_PreBool`)   |
| `K2Node_IfThenElse_0`    | `K2Node_IfThenElse`     | `Branch`                                           |
| `K2Node_VariableSet_0`   | `K2Node_VariableSet`    | `Set FootLOffset` (Vector 형, Value=(0,0,0))       |
| `K2Node_VariableSet_1`   | `K2Node_VariableSet`    | `Set FootROffset` (Vector 형, Value=(0,0,0))       |
| `K2Node_VariableSet_2`   | `K2Node_VariableSet`    | `Set FootROffset_X/Y/Z` (분해형, 모두 0)           |
| `K2Node_VariableSet_3`   | `K2Node_VariableSet`    | `Set FootLOffset_X/Y/Z` (분해형, X=0/Y=0/**Z=20**) |

### 4.2 연결도

```
[Event BlueprintUpdateAnimation]
   .then    ─ ❌ 미연결 (이것이 데드 체인의 원인)
   .DeltaTimeX ─ 미사용

[Try Get Pawn Owner] ──ReturnValue──► [Get Movement Component].self
                                       │
                                       └─ReturnValue──► [Is Falling].self
                                                          │
                                                          └─ReturnValue──► [NOT Boolean].A
                                                                              │
                                                                              └─ReturnValue──► [Branch].Condition

[Branch]
   .execute  ─ ❌ 미연결
   .then     ──► [Set FootROffset_X/Y/Z (0,0,0)]──► [Set FootLOffset_X/Y/Z (0,0,20)]
   .else     ──► [Set FootLOffset Vec (0,0,0)]   ──► [Set FootROffset Vec (0,0,0)]
```

### 4.3 실행 시 가정 분기 (참고)

`Branch.execute` 가 연결되었다고 가정한 분기 동작:

| Condition (`NOT IsFalling`) | 의미   | then/else | 실제 수행                                       |
|----------------------------|--------|-----------|-------------------------------------------------|
| `true`                     | 지상   | `then`    | `FootROffset = (0,0,0)`, `FootLOffset = (0,0,20)` |
| `false`                    | 공중   | `else`    | `FootLOffset = (0,0,0)`, `FootROffset = (0,0,0)` |

> 위 동작은 현재 실행되지 않는다. 결과/의도/검토는 `FootPlacement_Troubleshooting.md` §1 참고.

---

## 5. Idle_B (Animation Sequence)

| 항목                | 값                                                   |
|---------------------|------------------------------------------------------|
| Skeleton            | `Mage_Skeleton`                                      |
| Duration            | 2.1333334 s                                          |
| Num Frames          | 64                                                   |
| Num Keys            | 65                                                   |
| Sample / Frame Rate | 30 fps                                               |
| Is Looping          | `false`                                              |
| Has Root Motion     | `false`                                              |
| Force Root Lock     | `false`                                              |
| Root Motion Lock    | `RefPose`                                            |
| Additive Type       | `None`                                               |
| Interpolation       | `Linear`                                             |
| Rate Scale          | 1.0                                                  |
| Compression         | `Default`                                            |

---

## 6. CR_Mage_FootIK — Control Rig

### 6.1 기본 정보

| 항목               | 값                          |
|--------------------|-----------------------------|
| Parent Class       | `ControlRig`                |
| 전체 본            | 26 (실제 23 + 가상 3)       |
| Animatable Control | 0                           |
| Null               | 0                           |
| Curve              | 0                           |
| Blueprint 함수     | 1 (`FootTrace`)             |
| Blueprint 변수     | 6                           |
| 그래프             | 2 (`Rig`(root), `FootTrace`) |
| 루트 그래프 노드   | 36                          |
| 루트 그래프 링크   | 37                          |

### 6.2 Blueprint 변수 (6)

| 이름               | 타입    | 의미                                                  |
|--------------------|---------|-------------------------------------------------------|
| `ShouldDoIKTrace`  | bool    | true 면 트레이스 수행, false 면 타깃 오프셋 0 리셋    |
| `ZOffset_L_Target` | double  | 좌측 발 트레이스 직후의 raw 목표 Z (보간 전)          |
| `ZOffset_R_Target` | double  | 우측 발 트레이스 직후의 raw 목표 Z (보간 전)          |
| `ZOffset_L`        | double  | 보간된 좌측 발 Z 오프셋 (실제 적용 값)                 |
| `ZOffset_R`        | double  | 보간된 우측 발 Z 오프셋 (실제 적용 값)                 |
| `ZOffset_Pelvis`   | double  | 펠비스(hips) Z 오프셋 = min(ZOffset_L, ZOffset_R)    |

### 6.3 루트 그래프 (`Rig`)

`BeginExecution` → `SequenceExecution` 노드가 A/B/C/D 4 갈래를 순차 실행.

```
BeginExecution
    │
    ▼
SequenceExecution
    ├── A ──► Trace 분기 (ShouldDoIKTrace)
    ├── B ──► AlphaInterp (Target → Smoothed)
    ├── C ──► VB Foot_L/R + hips ModifyTransforms
    └── D ──► PBIK 솔브
```

#### 단계 A — Trace 분기

```
ShouldDoIKTrace (Variable Get)
        │
        ▼
RigVMFunction_ControlFlowBranch
   ├─ True  ─► FootTrace(VB Foot_L)─HitLocation.Z─► Set ZOffset_L_Target
   │             │
   │             └─► FootTrace(VB Foot_R)─HitLocation.Z─► Set ZOffset_R_Target
   └─ False ─► Set ZOffset_L_Target (Value 핀 미연결 → 0)
               Set ZOffset_R_Target (Value 핀 미연결 → 0)
```

`FootTrace` 함수 본체는 §6.4.

#### 단계 B — AlphaInterp 보간

`RigVMFunction_AlphaInterp` 2 개. 좌/우 동일 파라미터.

| 파라미터                    | 값        |
|-----------------------------|-----------|
| `Scale`                     | 1.000000  |
| `Bias`                      | 0.000000  |
| `bMapRange`                 | false     |
| `InRange` / `OutRange`      | (0, 1)    |
| `bClampResult`              | false     |
| `ClampMin` / `ClampMax`     | 0 / 1     |
| `bInterpResult`             | true      |
| `InterpSpeedIncreasing`     | 15.000000 |
| `InterpSpeedDecreasing`     | 15.000000 |

흐름:

```
Get ZOffset_L_Target ──► AlphaInterp   ──► Set ZOffset_L
Get ZOffset_R_Target ──► AlphaInterp_1 ──► Set ZOffset_R
```

#### 단계 C — 가상 본 + 펠비스 변형

`RigUnit_ModifyTransforms` 3 개. 모두 `Mode = AdditiveGlobal`.

| ModifyTransforms   | Item (Bone)    | Translation.Z 입력      | Weight |
|--------------------|----------------|--------------------------|--------|
| `ModifyTransforms` | `VB Foot_L`    | `ZOffset_L` (Variable)   | 1.0    |
| `ModifyTransforms_1` | `VB Foot_R`  | `ZOffset_R` (Variable)   | 1.0    |
| `ModifyTransforms_2` | `hips`       | `ZOffset_Pelvis` (Variable) | 1.0 |

`ZOffset_Pelvis` 계산:

```
Get ZOffset_L ─► Less.A ┐
Get ZOffset_R ─► Less.B ┴─► (L < R) ─► If.Condition
Get ZOffset_L ──────────────────────────► If.True
Get ZOffset_R ──────────────────────────► If.False
                                          If.Result ─► Set ZOffset_Pelvis
```

즉 `ZOffset_Pelvis = min(ZOffset_L, ZOffset_R)`.

#### 단계 D — PBIK 솔브

`RigUnit_PBIK` 1 개.

| 파라미터                                  | 값             |
|-------------------------------------------|----------------|
| `Root`                                    | `hips`         |
| `Iterations`                              | 20             |
| `SubIterations`                           | 0              |
| `MassMultiplier`                          | 1.0            |
| `bAllowStretch`                           | false          |
| `RootBehavior`                            | `PinToInput`   |
| `MaxAngle`                                | 30°            |
| `OverRelaxation`                          | 1.3            |
| `GlobalPullChainAlpha`                    | 1.0            |
| `PrePullRootSettings.RotationAlpha`       | 0.0            |
| `PrePullRootSettings.PositionAlpha`       | 1.0            |
| `Debug.bDrawDebug`                        | false          |
| `BoneSettings`                            | (없음)         |
| `ExcludedBones`                           | (없음)         |

Effectors:

| Index | Bone     | Transform (입력)                           | PositionAlpha | RotationAlpha | StrengthAlpha | ChainDepth | PullChainAlpha | PinRotation |
|-------|----------|--------------------------------------------|---------------|---------------|---------------|-----------|----------------|-------------|
| 0     | `foot_l` | `GetTransform(VB Foot_L, GlobalSpace)`     | 1.0           | 1.0           | 1.0           | 0         | 1.0            | 1.0         |
| 1     | `foot_r` | `GetTransform(VB Foot_R, GlobalSpace)`     | 1.0           | 1.0           | 1.0           | 0         | 1.0            | 1.0         |

### 6.4 함수 그래프 `FootTrace` (11 노드)

#### 시그니처

| 종류    | 이름           | 타입             |
|---------|----------------|------------------|
| Input   | `Item`         | `FRigElementKey` |
| Output  | `HitLocation`  | `FVector`        |

#### 노드/연결

```
Entry(Item)
   ├─► Get Transform A
   │       Item = (Bone) Entry.Item        ← 호출자가 넘긴 발 가상 본 (VB Foot_L/R)
   │       Space = GlobalSpace
   │       bInitial = false
   │       .Translation ─► SphereTrace.Start
   │
   ├─ Get Transform B (Entry exec 와 분리, 순수 노드)
   │       Item = (Bone) "VB Foot_Root"
   │       Space = GlobalSpace
   │       .Translation ─► SphereTrace.End
   │
   ├─ SphereTraceByTraceChannel
   │       Start         ◄ Get Transform A.Translation
   │       End           ◄ Get Transform B.Translation
   │       TraceChannel  = TraceTypeQuery1
   │       Radius        = 5.000000
   │       HitLocation ─► Return.HitLocation
   │
   └─► Return(HitLocation)

(디버그 분기 — 실행선 미연결, 비활성)
   Break RigElementKey  ─► To String  ─► Concat ─► Print
   Get Transform A.Translation ─► To String_1 ─► Concat.A
   Get Transform B.Translation ─► To String_2 ─► Concat.C
```

Print 노드의 `ExecuteContext` 입력 핀은 `Entry → Return` 의 exec 라인에 연결되어 있지 않다 → **실행되지 않는다.**

### 6.5 노드 인벤토리 (루트 그래프 36 노드)

| 클래스                            | 수 |
|-----------------------------------|----|
| `RigVMUnitNode` (`RigUnit_*`)     | 12 |
| `RigVMVariableNode`               | 18 |
| `RigVMRerouteNode`                | 4  |
| `RigVMDispatchNode` (`If`)        | 1  |
| `RigVMFunctionReferenceNode` (`FootTrace`) | 2 |

이름 충돌이 있어 다음 두 노드만 명시: `FootTrace`, `FootTrace_1` (좌/우 호출).

---

## 7. IK_Mage — IK Rig (현재 비활성)

| 항목              | 값                                                  |
|-------------------|-----------------------------------------------------|
| Preview Mesh      | `Mage`                                              |
| Pelvis Bone       | `None` (미지정)                                     |
| 전체 본           | 23                                                  |
| Solver            | 1 — `IKRigFullBodyIKSolver` (`hips` 시작, enabled)  |
| Goal              | 4 — `hand_l_Goal`, `hand_r_Goal`, `foot_l_Goal`, `foot_r_Goal` (모두 connected) |
| Retarget Chain    | 0                                                   |

> ABP_Mage AnimGraph 의 `IK Rig` 노드가 미연결이므로 본 솔버는 현재 어떤 포즈에도 영향을 주지 않는다. 살리는 방법은 `FootPlacement_Troubleshooting.md` §5 참고.

---

## 8. 분석 메서드 (재현용)

본 문서는 다음 Monolith MCP 호출들로 수집한 데이터를 바탕으로 작성됨.

```
animation_query / get_abp_info               (ABP_Mage)
animation_query / get_abp_variables          (ABP_Mage)
animation_query / get_abp_linked_assets      (ABP_Mage)
animation_query / get_nodes                  (ABP_Mage, AnimGraph / EventGraph)
blueprint_query / get_graph_data             (ABP_Mage, AnimGraph)
blueprint_query / get_graph_data             (ABP_Mage, EventGraph)

animation_query / get_ikrig_info             (IK_Mage)

animation_query / get_control_rig_info       (CR_Mage_FootIK)
animation_query / get_control_rig_variables  (CR_Mage_FootIK)
animation_query / get_control_rig_graph      (CR_Mage_FootIK)
blueprint_query / list_graphs                (CR_Mage_FootIK)
blueprint_query / get_functions              (CR_Mage_FootIK)
blueprint_query / get_graph_data             (CR_Mage_FootIK, FootTrace)

animation_query / get_skeleton_info          (Mage_Skeleton)
animation_query / get_sequence_info          (Idle_B)
blueprint_query / get_cdo_properties         (BP_Mage)
blueprint_query / get_components             (BP_Mage)
```

Control Rig 루트 그래프 응답이 대용량 단일 라인 JSON 으로 떨어져, 다음 보조 스크립트로 노드/링크/핀을 구조화해 정리함.

- `Docs/Tools/dump_rig.py` — JSON 을 받아 노드/핀/링크를 사람이 읽을 수 있게 출력.

---

## 9. 용어

| 약어 / 용어        | 풀어쓰기 / 의미                                                  |
|--------------------|------------------------------------------------------------------|
| ABP                | Animation Blueprint                                              |
| CR                 | Control Rig                                                      |
| IK                 | Inverse Kinematics                                               |
| FBIK               | Full Body IK (IK Rig 의 한 솔버 타입)                            |
| PBIK               | Position-Based IK (Control Rig 의 한 솔버 노드, `RigUnit_PBIK`) |
| VB (Virtual Bone)  | 스켈레톤에 추가되는 “source 본 위치 + target 본까지의 상대 트랜스폼” 본 |
| AdditiveGlobal     | `RigUnit_ModifyTransforms` 모드 중 하나. 글로벌 트랜스폼에 더함 |
| `SequenceExecution`| 실행 핀(A/B/C/D)을 순서대로 한 번씩 실행                          |

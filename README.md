# CustomFootIK

> Unreal Engine 5.7 기반 **Foot Placement(Foot IK) 학습 프로젝트**.
> Mage 캐릭터의 발이 경사면 · 계단 등 지면에 자연스럽게 정합되도록, 스켈레톤의 가상 본(Virtual Bone)과 Control Rig(PBIK)로 구현했다. 같은 가상 본 인프라 위에 IK Rig(FBIK) 경로로 갈아끼우는 학습 과제도 함께 다룬다.

---

## 📖 학습 문서 (GitHub Pages)

👉 **<https://bong9tutor.github.io/CustomFootIK/Html/>**

> 진입 흐름: `https://bong9tutor.github.io/CustomFootIK/` 는 본 README 를 자동 렌더 (entry). `Html/index.html` 이 3 개 문서 카드 페이지.

Diataxis 프레임 기반 3 분할.

| 문서 | 위치 | 어떤 사람이 본다 |
|---|---|---|
| **Learning** | `Html/FootPlacement_Learning.html` | 처음 본 사람 — 멘탈 모델 형성 (목표, 활성 경로, Control Rig 4 단계, 확인 과제) |
| **Implementation Reference** | `Html/FootPlacement_ImplementationReference.html` | 정확한 값이 필요한 사람 — 노드/핀/파라미터 전체 표 SSOT |
| **Troubleshooting** | `Html/FootPlacement_Troubleshooting.html` | 결함 · 확장 · 비활성 경로 살리기 |

각 페이지는 좌측에 sticky 사이드바(문서 세트 nav + 자기 문서 TOC) 가 있고, `검증됨 / 추론 / 주의 / 확장` 4 색 라벨 + 4 종 콜아웃(`확인 / 주의 / 확장 / 메모`) + Mermaid 다이어그램으로 구성된다.

GitHub Pages 활성화 방법은 §"GitHub Pages 배포" 참고.

---

## 🎯 한 줄 요약

> **가상 본 = “발의 목표 위치 마커”. PBIK = “그 마커로 실제 발 본을 끌어당기는 솔버”.**

```
Idle_B  ──►  CR_Mage_FootIK (Control Rig)  ──►  Output Pose
              │
              ├─ A. Foot Trace (Sphere)
              ├─ B. AlphaInterp (15/sec)
              ├─ C. Modify VB Foot_L/R + hips (AdditiveGlobal)
              └─ D. PBIK 솔브 (foot_l/r → VB Foot_L/R 따라가기)
```

`IK_Mage` (IK Rig) 와 ABP 변수 `FootL/ROffset` 은 인프라만 깔린 비활성 확장 경로다. 살리는 단계는 Troubleshooting §5 참고.

---

## 🗂 디렉터리 구조

```
CustomFootIK/
├── README.md                            ← 본 파일 (GitHub repo 메인 + GitHub Pages entry)
├── CLAUDE.md                            ← Claude Code 작업 가이드
├── CustomFootIK.uproject
│
├── Source/CustomFootIK/                 ← C++ (캐릭터/카메라/입력만, Foot IK 미관여)
├── Content/
│   ├── Characters/Mage/
│   │   ├── SkeletalMeshes/Mage_Skeleton (← 가상 본 3개 포함)
│   │   └── Rigs/
│   │       ├── IK_Mage         (IK Rig, FullBodyIK 솔버, 현재 비활성)
│   │       └── CR_Mage_FootIK  (Control Rig, 실제 활성 Foot IK 로직)
│   └── CustomFootIK/
│       ├── BP_Mage             (캐릭터 BP)
│       └── ABP_Mage            (Animation Blueprint)
│
├── Docs/                                ← 마크다운 원본 + 빌드 도구
│   ├── FootPlacement_Learning.md
│   ├── FootPlacement_ImplementationReference.md
│   ├── FootPlacement_Troubleshooting.md
│   └── Tools/
│       ├── md_to_html.py        (마크다운 → HTML 변환)
│       ├── dump_rig.py          (Control Rig RigVM JSON 파서)
│       ├── verify_html.py       (HTML 출력 검증)
│       └── scan_perms.py        (Claude Code 권한 사용량 분석)
│
├── Html/                                ← 빌드된 HTML (GitHub Pages 가 serve)
│   ├── index.html                       ← 3개 문서 카드 랜딩 페이지
│   ├── FootPlacement_Learning.html
│   ├── FootPlacement_ImplementationReference.html
│   └── FootPlacement_Troubleshooting.html
│
├── Plugins/
│   └── Monolith/                        ← UE 에디터 인스펙션 MCP 서버 (포트 9316)
│
└── .claude/settings.json                ← Claude Code 권한 설정 (Monolith/JetBrains MCP 등 자동 허용)
```

---

## ✅ 사전 준비

| 도구 | 버전 / 비고 |
|---|---|
| Unreal Engine | **5.7** (`++UE5+Release-5.7-CL-51494982` 빌드 기준) |
| Git LFS | 필수. `.gitattributes` 가 `*.uasset`, `*.umap` 을 LFS 추적. `git lfs install` 후 클론. |
| Python | 3.10+ (문서 빌드용). `pip install markdown` 필요 |
| (선택) Rider | C++ 측 작업 시. `Plugins/Developer/RiderLink` 는 .gitignore |

```bash
# 클론
git lfs install
git clone https://github.com/bong9tutor/CustomFootIK.git
cd CustomFootIK

# 문서 빌드용 의존성
pip install markdown
```

UE 에디터는 `CustomFootIK.uproject` 더블 클릭 → 빌드 진행.

---

## 🛠 문서 빌드

마크다운 3 종 → HTML 3 종 일괄 변환.

```bash
python Docs/Tools/md_to_html.py
```

출력 (예시):
```
Converting doc set:
  [learning      ] FootPlacement_Learning.md            -> FootPlacement_Learning.html            (26,792 chars)
  [reference     ] FootPlacement_ImplementationReference.md -> ...Reference.html                   (33,961 chars)
  [troubleshooting] FootPlacement_Troubleshooting.md     -> FootPlacement_Troubleshooting.html     (26,690 chars)
```

산출물 검증:

```bash
python Docs/Tools/verify_html.py
```

각 HTML 의 제목 / heading 개수 / 라벨 배지 수 / 콜아웃 박스 수 / Mermaid 블록 수 / TOC 항목 / 문서 nav 상태를 리포트한다.

### 마크다운 작성 규칙 (변환기가 이해하는 것)

| 문법 | 결과 |
|---|---|
| `{검증됨}` / `{추론}` / `{주의}` / `{확장}` | 인라인 라벨 배지 (녹/보라/주황/청록) |
| `:::verify ... :::` / `:::caution` / `:::extend` / `:::note` | 콜아웃 박스 (각 4종) |
| ` ```mermaid ` 코드 펜스 | Mermaid 10.9 다이어그램 (라이트/다크 자동) |

Mermaid 라벨에 `(`, `)`, `<`, `>`, `:`, `/`, `,` 가 포함되면 **반드시 따옴표로 감쌀 것** — `["..."]`, `(["..."])`, `{"..."}`. HTML entity (`&lt;`, `&#40;`) 는 사용 금지.

---

## 🚀 GitHub Pages 배포

리포지토리 Settings 에서 한 번만 설정.

1. **Settings → Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `master` (또는 기본 브랜치) / **Folder**: `/ (root)`
4. **Save**

활성화되면 다음 두 URL 이 동작:

| URL                                                                | 컨텐츠                                  |
|--------------------------------------------------------------------|-----------------------------------------|
| `https://bong9tutor.github.io/CustomFootIK/`                       | GitHub jekyll 가 본 README.md 를 자동 렌더 (repo entry) |
| `https://bong9tutor.github.io/CustomFootIK/Html/`                  | **3 개 문서 카드 랜딩** (`Html/index.html`) |
| `https://bong9tutor.github.io/CustomFootIK/Html/FootPlacement_Learning.html` | Learning 문서 (Reference / Troubleshooting 도 같은 형식) |

> root 에는 별도 `index.html` 을 두지 않는다 — repo 페이지와 Pages 페이지가 모두 README.md 한 곳에서 출발하게 단일화.

문서 갱신 워크플로우:

```bash
# 1) 마크다운 편집
vim Docs/FootPlacement_Learning.md

# 2) HTML 재빌드
python Docs/Tools/md_to_html.py

# 3) 검증
python Docs/Tools/verify_html.py

# 4) 커밋 & 푸시 (Git LFS 가능한 환경 필요)
git add Docs/ Html/
git commit -m "docs: update Learning §X.Y"
git push
```

푸시 후 1~2 분 안에 Pages 가 자동 재배포.

---

## 🤖 MCP 활용 (선택, 분석 / 자동화용)

본 프로젝트는 두 MCP 서버를 활용하도록 `.claude/settings.json` 이 미리 설정되어 있다.

### Monolith MCP (`mcp__monolith__*`)
- `Plugins/Monolith` 가 UE 에디터 안에서 HTTP 서버(포트 9316)를 띄움. `.mcp.json` 이 Python 프록시로 Claude Code 와 연결.
- 도구: `blueprint_query`, `animation_query`, `material_query`, `mesh_query`, `source_query`, `config_query`, `monolith_discover`, `monolith_guide` 등 21 개.
- 모든 `.uasset` (Blueprint / Animation BP / Control Rig / IK Rig / Skeleton / Material / Mesh) 인스펙션과 일부 수정 가능.
- **에디터가 켜져 있어야 동작**.

### JetBrains MCP (`mcp__jetbrains__*`)
- Rider IDE 직결. C++ 측 작업 — 심볼 점프, 솔루션 빌드, 리팩터링, 검색, 인스펙션.
- 도구 41 개 (search/get 계열 + build_solution, execute_run_configuration 등).
- **Rider 가 켜져 있어야 동작**.

도구 선택 규칙:
- 일반 파일 작업 → Read/Edit
- C++/솔루션 차원 → JetBrains MCP
- `.uasset`/Blueprint/Animation/Material 차원 → **Monolith MCP 우선** (Read 로는 LFS 포인터만 보임)

---

## 📁 핵심 에셋 5 종 (Foot IK 학습 대상)

| 에셋 | 경로 | 역할 |
|---|---|---|
| `Mage_Skeleton` | `Content/Characters/Mage/SkeletalMeshes/` | 실제 본 23 + 가상 본 3 (VB Foot_Root, VB Foot_L, VB Foot_R) |
| `IK_Mage` | `Content/Characters/Mage/Rigs/` | IK Rig, FullBodyIK 솔버, 골 4 (양손양발). **현재 비활성** |
| `CR_Mage_FootIK` | `Content/Characters/Mage/Rigs/` | Control Rig, **실제 활성 Foot IK 로직** (트레이스 → 보간 → 변형 → PBIK) |
| `ABP_Mage` | `Content/CustomFootIK/` | Animation Blueprint, AnimGraph 가 Control Rig 호출 |
| `BP_Mage` | `Content/CustomFootIK/` | 캐릭터 BP, 위 메시·ABP 사용 |

수정 작업은 거의 위 5 개 사이에서 이뤄지며, C++ 변경은 드물다.

---

## 📝 라이선스 / 기여

학습 용도의 사적 프로젝트. PR / 이슈 환영.

UE 5 ThirdPerson 템플릿에서 출발해 Mage 캐릭터·Foot IK 관련 자산만 학습 단계별로 추가했다. 자세한 커밋 이력은 `git log` 참고.

Claude Code 와의 협업 가이드는 [`CLAUDE.md`](./CLAUDE.md) 에 정리됨.

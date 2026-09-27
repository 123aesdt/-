# 自然动作数字人 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将单张医生照片制作成带自然眨眼、轻微头动和呼吸感的循环头像素材，同时保留现有 Wav2Lip 口型、Qwen、TTS 和 WebRTC 链路。

**Architecture:** LivePortrait 只在算力云上作为离线素材生成器运行，以医生照片和官方中性驱动模板生成 25 FPS 动作视频；现有 `avatars/wav2lip/genavatar.py` 再把视频转换成 LiveTalking Avatar。运行时继续只加载 Wav2Lip，并通过新的头像 ID 切换；旧头像目录保持不动，便于立即回退。

**Tech Stack:** Python 3.10 Conda 环境、LivePortrait、FFmpeg、OpenCV、PyTorch、LiveTalking Wav2Lip、PowerShell/Pytest 验证。

**Spec:** `docs/superpowers/specs/2026-09-22-realtime-expressive-avatar-design.md`

## Global Constraints

- 不修改 Qwen、TTS、WebRTC 和医疗业务接口。
- LivePortrait 不进入 LiveTalking 实时进程，不增加在线推理显存和延迟。
- 输出素材固定为 25 FPS，人物动作克制，嘴部尽量保持中性。
- 新头像使用 `medical_doctor_natural`，旧 `medical_doctor_photo` 不覆盖。
- 未通过资源完整性、循环连续性和 WebRTC 验证时，不切换默认头像。
- 不清理或覆盖工作区中用户已有的未提交改动。

## Review Focus

- LivePortrait 输出可能包含拼接对比画面：Avatar 生成前必须确认只截取最终人物结果。
- 驱动视频嘴部动作过大：输出必须使用唇部归一化，避免与 Wav2Lip 二次口型冲突。
- 视频首尾跳变：使用镜像循环或截取安全区段，并检测首尾平均像素差。
- 人脸框数量与完整帧数量不一致：验证器必须返回非零退出码，禁止启动新头像。
- 新头像启动失败：`start.sh` 必须允许通过 `AVATAR_ID` 环境变量切回旧头像。

---

### Task 1: Avatar 资源验证器与可回退启动参数

**Files:**
- Create: `tools/validate_avatar_asset.py`
- Create: `tests/test_validate_avatar_asset.py`
- Modify: `start.sh`

**Interfaces:**
- Consumes: Avatar 目录中的 `full_imgs/*.png`、`face_imgs/*.png`、`coords.pkl`。
- Produces: `validate_avatar(path: Path, min_frames: int = 50) -> ValidationResult`；命令行验证成功返回 0，失败返回 1；`start.sh` 接受可选环境变量 `AVATAR_ID`。

- [ ] **Step 1: 写资源验证器失败测试**

```python
def test_rejects_mismatched_frame_and_coordinate_counts(tmp_path):
    avatar = build_avatar_fixture(tmp_path, full=3, face=3, coords=2)
    result = validate_avatar(avatar, min_frames=1)
    assert not result.ok
    assert "数量不一致" in result.message

def test_accepts_complete_dynamic_avatar(tmp_path):
    avatar = build_avatar_fixture(tmp_path, full=3, face=3, coords=3)
    result = validate_avatar(avatar, min_frames=1)
    assert result.ok
```

- [ ] **Step 2: 运行测试确认 RED**

Run: `python -m pytest tests/test_validate_avatar_asset.py -v`

Expected: FAIL，原因是 `tools.validate_avatar_asset` 尚不存在。

- [ ] **Step 3: 实现最小验证器**

验证以下条件并输出中文错误：目录存在、`coords.pkl` 可读取、完整帧/人脸帧/坐标数量一致、帧数不少于阈值、所有图片可由 OpenCV 打开且尺寸一致。

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `python -m pytest tests/test_validate_avatar_asset.py -v`

Expected: 所有用例 PASS。

- [ ] **Step 5: 为启动脚本写失败测试**

在 `tests/Test-WindowsLauncher.ps1` 相同的静态脚本验证方式下，新增断言确认 `start.sh` 使用 `${AVATAR_ID:-medical_doctor_photo}`，并在启动前调用资源验证器。

- [ ] **Step 6: 运行测试确认 RED**

Run: `pwsh -File tests/Test-WindowsLauncher.ps1`

Expected: FAIL，提示启动脚本尚未支持可配置 Avatar ID 或资源验证器。

- [ ] **Step 7: 修改启动脚本并确认 GREEN**

将固定值改为 `AVATAR_ID="${AVATAR_ID:-medical_doctor_photo}"`，并在启动前执行：

```bash
python tools/validate_avatar_asset.py "$AVATAR_DIR" --min-frames 50
```

Run: `pwsh -File tests/Test-WindowsLauncher.ps1`

Expected: PASS。

### Task 2: 在算力云离线生成自然动作视频

**Files:**
- Remote create: `/root/autodl-tmp/LivePortrait/`
- Remote create: `/root/autodl-tmp/LiveTalking/data/natural-avatar/doctor-natural.mp4`
- Remote consume: `/root/autodl-tmp/LiveTalking/web/assets/doctor-li-yanyan.png`

**Interfaces:**
- Consumes: 原始医生 PNG、LivePortrait 官方中性驱动视频或动作模板。
- Produces: 720×900、25 FPS、8～10 秒、无音频的自然动作 MP4。

- [ ] **Step 1: 安装独立离线环境**

在 `/root/autodl-tmp` 创建 Python 3.10 Conda 环境 `liveportrait`，安装 FFmpeg，并克隆官方 `KlingAIResearch/LivePortrait`。依照官方 README 下载 `pretrained_weights`，不修改 LiveTalking 当前 Python 3.12 环境。

- [ ] **Step 2: 验证离线环境**

Run: `conda run -n liveportrait python /root/autodl-tmp/LivePortrait/inference.py -h`

Expected: 退出码 0，帮助中包含 `--source`、`--driving` 和 `--output-dir`。

- [ ] **Step 3: 生成第一版动作视频**

使用官方正脸中性驱动素材，启用唇部归一化、完整表情与姿态区域、半精度推理；保持源图身份和背景，输出到独立目录。不得直接写入现有 Avatar 目录。

- [ ] **Step 4: 标准化成 LiveTalking 素材**

使用 FFmpeg 仅保留最终生成画面，去除音频，缩放并补边到 720×900，转为 25 FPS；截取动作幅度最稳定的 8～10 秒。若首尾姿态不接近，构造正放/倒放镜像循环。

- [ ] **Step 5: 验证视频技术指标**

Run: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames -show_entries format=duration -of json /root/autodl-tmp/LiveTalking/data/natural-avatar/doctor-natural.mp4`

Expected: `720×900`、`25/1`、时长 8～10 秒、帧数至少 200。

- [ ] **Step 6: 抽帧检查身份与动作**

抽取第 1、50、100、150、200 帧，确认五官、白大褂、听诊器和背景无明显漂移；眨眼、头动和肩部起伏可见但幅度克制，嘴部没有持续讲话动作。

### Task 3: 重建新 Avatar、切换并验证实时链路

**Files:**
- Remote create: `/root/autodl-tmp/LiveTalking/data/avatars/medical_doctor_natural/`
- Remote modify: `/root/autodl-tmp/LiveTalking/start.sh`
- Local modify: `start.sh`

**Interfaces:**
- Consumes: `doctor-natural.mp4`。
- Produces: `full_imgs`、`face_imgs`、`coords.pkl`，并可通过 `AVATAR_ID=medical_doctor_natural ./start.sh` 启动。

- [ ] **Step 1: 使用现有生成器创建新 Avatar**

Run:

```bash
python avatars/wav2lip/genavatar.py \
  --video_path data/natural-avatar/doctor-natural.mp4 \
  --avatar_id medical_doctor_natural \
  --save_path data/avatars \
  --face_det_batch_size 16
```

Expected: 新目录生成成功，旧 `medical_doctor_photo` 目录保持不变。

- [ ] **Step 2: 执行资源验证器**

Run: `python tools/validate_avatar_asset.py data/avatars/medical_doctor_natural --min-frames 200`

Expected: 返回 0，完整帧、人脸帧和坐标数量一致。

- [ ] **Step 3: 同步经过测试的启动脚本并切换服务**

先记录旧 LiveTalking PID，只终止命令行同时包含当前项目 `app.py` 和旧 Avatar ID 的进程；不停止 coturn。然后执行：

```bash
AVATAR_ID=medical_doctor_natural ./start.sh
```

- [ ] **Step 4: 验证服务和接口**

Run: `curl -fsS http://127.0.0.1:8010/index.html >/dev/null`

Run: `tail -n 200 livetalking.log`

Expected: 页面返回 200；日志包含新 Avatar ID，且没有缺失资源、人脸检测或 CUDA OOM 错误。

- [ ] **Step 5: 验证 WebRTC、文字回答和动作**

在现有 SSH 隧道页面连接 WebRTC，发送“请简单介绍高血压的日常注意事项”。确认 Qwen 产生回答、TTS 有声音、Wav2Lip 嘴型同步；待机时有眨眼和呼吸，回答时有轻微头动，连续播放 30 秒无明显首尾跳变。

- [ ] **Step 6: 性能和回退验证**

从日志记录 `inferfps` 和 `finalfps`，两者应不低于 25。若新头像失败，执行 `AVATAR_ID=medical_doctor_photo ./start.sh` 恢复旧头像，并保留新素材和失败日志供诊断。

- [ ] **Step 7: 运行本地完整回归测试**

Run: `python -m pytest -q`

Run: `pwsh -File tests/Test-EnterpriseUI.ps1`

Run: `pwsh -File tests/Test-TurnTunnel.ps1`

Run: `pwsh -File tests/Test-WindowsLauncher.ps1`

Expected: 所有测试退出码为 0；若仓库已有无关失败，逐项记录测试名和原始错误，不把它们描述成通过。

# Task1: TCP 抓包分析与实现说明

> 作者: 孙墨涵  学号: 241002615

---

## 一、Wireshark 抓包截图

> **截图环境**: 127.0.0.1:18888, Lmin=10, Lmax=15, Seed=42, N=4 块

### 1.1 Type=1 — Initialization 报文

**方向**: Client → Server (源端口 577xx → 目标端口 18888)

| 截图 |
|------|
| **(在此粘贴 Type=1 的截图)** |

**识别要点**: TCP payload 前 2 字节为 `00 01`，后 4 字节为 N 值

---

### 1.2 Type=2 — agree 报文

**方向**: Server → Client (源端口 18888 → 目标端口 577xx)

| 截图 |
|------|
| **(在此粘贴 Type=2 的截图)** |

**识别要点**: TCP payload 仅 2 字节 `00 02`

---

### 1.3 Type=3 — reverseRequest 报文 (4 个)

**方向**: Client → Server，以下任选 1~2 个截图

| 截图 1 (如第 1 块，长度=15) |
|------|
| **(在此粘贴 Type=3 截图)** |

| 截图 2 (可选) |
|------|
| **(在此粘贴)** |

**识别要点**: TCP payload 前 2 字节为 `00 03`，后面紧跟 ASCII 原文

---

### 1.4 Type=4 — reverseAnswer 报文 (4 个)

**方向**: Server → Client，以下任选 1~2 个截图

| 截图 1 (如第 1 块，长度=15) |
|------|
| **(在此粘贴 Type=4 截图)** |

| 截图 2 (可选) |
|------|
| **(在此粘贴)** |

**识别要点**: TCP payload 前 2 字节为 `00 04`，后面紧跟已反转的 ASCII 文本

---

### 1.5 完整交互流程

| 截图 — 完整包列表 (含 TCP 三次握手 → 4 种报文 → 四次挥手) |
|------|
| **(在此粘贴完整流程截图)** |

**对照要点**: 截图中的时间戳应与 client_run_log.txt 中的时间戳能够对应。

---

## 二、实现关键点与解决方案

### 2.1 可复现的不定长分块

**关键点**: 验收时需要根据 seed 口算分块结果。

**解决方案** (`generate_chunks` 函数，reversetcpclient.py:15-35):
- 通过 Seed 参数调用 `random.seed(seed)`，确保同一种子每次运行分块一致
- 循环用 `random.randint(Lmin, Lmax)` 取随机长度，最后一块自动截取剩余字节

### 2.2 全局文本反转

**关键点**: 整个原始文件的完整反转，而非各块独立反转。

**解决方案** (reversetcpclient.py:120):
```python
final_reversed_text = decoded_text + final_reversed_text
```
将每块反转结果拼在前面的基础上，实现块级别全局倒序。

### 2.3 自定义报文格式

**关键点**: 4 种类型报文通过 Type 字段区分，大端字节序编解码。

**解决方案**: 全部使用 `struct.pack('!HI', ...)` 和 `struct.unpack('!HI', ...)` 进行网络字节序转换。

### 2.4 TCP 分包处理

**关键点**: TCP 是流式协议，单次 recv 可能收不满指定字节。

**解决方案** (`recv_exact` 函数，reversetcpserver.py:17-22):
循环接收直到凑满期望字节数，防止粘包/拆包问题。

### 2.5 多客户端并发

**关键点**: 服务端需同时处理多个客户端请求。

**解决方案** (reversetcpserver.py:117-121):
每个 accept 到的连接由独立 daemon 线程处理，互不阻塞。

---

## 三、掌握的知识点

通过完成本 Task，我熟悉并掌握了以下知识点：

1. **TCP Socket 编程**: socket() → bind()/connect() → sendall()/recv() → close() 完整流程
2. **TCP 流式特性**: 理解 TCP 无消息边界，需要在应用层自行界定报文
3. **应用层自定义协议**: 设计 Type/Length/Value 结构，定义 4 种报文类型
4. **struct 网络字节序**: `!HI` 大端字节序打包/解包
5. **多线程并发**: threading.Thread 实现一客户端一线程的处理模型
6. **Wireshark 抓包分析**: 过滤 TCP 流，查看应用层 payload 字节

---

## 四、Git 仓库 URL

**(在此填写你的 GitHub / Gitee 仓库地址)**

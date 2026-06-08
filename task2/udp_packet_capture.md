# Task2: UDP 抓包分析与实现说明

> **说明**: 请在此文档中插入 Wireshark 截图，并填写各部分内容。

---

## 一、Wireshark 抓包截图

### 1.1 四种报文类型截图

请在下方插入能清晰显示以下 4 种报文的截图：

| 报文类型 | 方向 | 格式 | 截图位置 |
|----------|------|------|----------|
| Type=1 握手请求 | Client → Server | Type(2B)+Reserved(2B)+EncryptedID(2B) | (插入截图) |
| Type=2 握手确认 | Server → Client | Type(2B)+Reserved(2B)+Reserved(2B) | (插入截图) |
| Type=3 数据包 | Client → Server | Type(2B)+SeqNo(2B)+Length(2B)+Data | (插入截图) |
| Type=4 ACK 确认 | Server → Client | Type(2B)+AckSeq(2B)+Reserved(2B)+Time(3B) | (插入截图) |

**截图要点**:
- 截图中的时间戳应与 udp_client_run_log.txt / udp_server_run_log.txt 对应
- 需能看到丢包重传场景 (有超时 → 重传的序列)

### 1.2 完整传输流程截图

插入一张覆盖完整交互过程的 Wireshark 截图，包括：
- 握手阶段 (Type=1 → Type=2)
- 数据传输阶段 (交替的 Type=3 和 Type=4)
- 丢包重传场景 (同一 SeqNo 多次出现)

---

## 二、实现关键点与解决方案

### 2.1 连接建立 (UDP 模拟 TCP 三次握手)

**关键点**: UDP 无连接，需在应用层自己实现连接建立。

**解决方案** (udpclient.py:38-50, udpserver.py:55-83):
- Client 发送握手请求 (Type=1)，携带 StudentID XOR 0x5A3C 加密值
- Server 验证: 对收到的值再次 XOR 0x5A3C，检查结果是否在 [0, 9999]
- 验证通过回复 Type=2，失败打印错误信息

### 2.2 字节级滑动窗口

**关键点**: 发送窗口固定为 400 字节（而非固定包数）。

**解决方案** (udpclient.py:93-111):
- 变量 `bytes_in_flight` 追踪当前在途字节数
- 发送前检查: `bytes_in_flight + packet_size <= 400` 才允许发送
- 收到 ACK 后从 `bytes_in_flight` 中减去对应数据字节
- 每包数据 40~80 字节随机 → 窗口可容纳 5~10 个包

### 2.3 GBN 累积确认

**关键点**: 服务端采用累积确认，客户端收到 ACK=N 后确认 1~N 号包全部收到。

**解决方案**:
- Server (udpserver.py:97-127): 收到期望序号 → 发送 ACK；收到乱序 → 重发最近 ACK
- Client (udpclient.py:132-150): while 循环将 base 推进到 ack_seq，释放窗口空间

### 2.4 超时重传

**关键点**: 300ms 超时 → Go-Back-N 重传。

**解决方案** (udpclient.py:155-170):
- `socket.settimeout(0.3)` 设置 300ms 超时
- 超时捕获后: `next_seq = base; bytes_in_flight = 0`
- 下次循环从 base 开始重新填满窗口

### 2.5 丢包模拟

**关键点**: 在用户态程序中模拟网络丢包。

**解决方案** (udpserver.py:90-93):
- 收到 Type=3 数据包后，以 20% 概率直接 `continue`，不发送任何响应
- 仅模拟 client→server 方向丢包 (server→client 假设可靠)

### 2.6 pandas 统计计算

**关键点**: 使用 pandas 计算 RTT 统计量，包括标准差。

**解决方案** (udpclient.py:177-179):
```python
rtt_series = pd.Series(rtt_values, name="RTT")
std_rtt = rtt_series.std()
```

---

## 三、掌握的知识点

通过完成本 Task，熟悉并掌握了以下知识点：

1. **UDP Socket 编程**: SOCK_DGRAM、sendto/recvfrom 的使用
2. **应用层可靠性协议设计**: 在无连接传输层之上构造可靠传输
3. **GBN (Go-Back-N) 滑动窗口协议**: 理解累积确认、窗口滑动、回退重传
4. **字节级窗口 vs 包级窗口**: 发送窗口按字节计算，非固定包数
5. **超时重传机制**: 定时器设置、Go-Back-N 回退策略
6. **应用层自定义协议设计**: 报文首部定义、字段编解码、加密验证
7. **随机丢包模拟**: 在应用层模拟网络不可靠性
8. **pandas 基础使用**: Series 创建、统计量计算 (mean/max/min/std)
9. **RTT 测量**: 发送时间记录、往返延迟计算
10. **Wireshark UDP 抓包分析**: 过滤 UDP 数据报、查看应用层 payload

---

## 四、Git 仓库 URL

(在此填写你的 GitHub/Gitee 仓库地址)

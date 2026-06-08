import socket
import struct
import sys
import time
import random
import datetime
import pandas as pd


def log_event(msg):
    """带时间戳的日志写入 udp_client_run_log.txt"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open("udp_client_run_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def main():
    if len(sys.argv) != 3:
        print("用法: python udpclient.py <ServerIP> <ServerPort>")
        sys.exit(1)

    # 每次启动时清空旧日志和旧统计文件
    open("udp_client_run_log.txt", "w", encoding="utf-8").close()
    open("udp_statistics.txt", "w", encoding="utf-8").close()

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 超时时间 300ms，用于检测丢包
    TIMEOUT = 0.3
    client_socket.settimeout(TIMEOUT)
    server_addr = (server_ip, server_port)

    # ================================================================
    # 阶段 1: 握手 — 模拟 TCP 连接建立
    # ================================================================
    STUDENT_ID = 2615  # 学号后4位
    encrypted_id = STUDENT_ID ^ 0x5A3C

    client_socket.sendto(struct.pack('!HHH', 1, 0, encrypted_id), server_addr)
    log_event(
        f"Send: 握手请求 (Type=1), "
        f"学号后4位={STUDENT_ID}, XOR加密值={encrypted_id}"
    )

    try:
        data, _ = client_socket.recvfrom(1024)
        if len(data) >= 2:
            msg_type = struct.unpack('!H', data[:2])[0]
            if msg_type != 2:
                print("[!] 握手失败：未收到 Type=2 确认报文")
                log_event("握手失败：未收到 Type=2 确认报文")
                return
        log_event("Recv: 握手确认 (Type=2)")
        print("[+] 握手成功！开始数据传输...\n" + "-" * 55)

        # ================================================================
        # 阶段 2: 准备 GBN 参数  (发送窗口 = 400 字节)
        # ================================================================
        TOTAL_PACKETS = 30                        # 共发送 30 个包
        WINDOW_SIZE_BYTES = 400                   # 窗口大小: 400 字节

        # ★ 修复点: 每个包的数据大小随机在 40~80 字节
        packet_sizes = [random.randint(40, 80) for _ in range(TOTAL_PACKETS)]

        # ★ 修复点: 提前计算每个包的字节范围
        byte_starts = []   # 第 n 个包的起始字节 (1-indexed)
        byte_ends = []     # 第 n 个包的结束字节 (1-indexed)
        cursor = 1
        for sz in packet_sizes:
            byte_starts.append(cursor)
            byte_ends.append(cursor + sz - 1)
            cursor += sz
        total_data_bytes = cursor - 1

        print(f"[*] 共 {TOTAL_PACKETS} 个包, 总数据 {total_data_bytes} 字节, "
              f"窗口={WINDOW_SIZE_BYTES}字节")
        log_event(
            f"初始化: TOTAL_PACKETS={TOTAL_PACKETS}, "
            f"WINDOW_SIZE={WINDOW_SIZE_BYTES}字节, "
            f"总数据={total_data_bytes}字节, "
            f"包大小范围=[{min(packet_sizes)},{max(packet_sizes)}]"
        )

        # GBN 状态变量
        base = 0              # 窗口左沿 (0-based index)
        next_seq = 0          # 下一个要发送的包 (0-based index)
        bytes_in_flight = 0   # 当前在途字节数

        total_transmissions = 0      # 实际总发送次数（含重传）
        send_times = {}              # seq_no(1-based) → 最近发送时间
        rtt_values = []              # 已确认包的 RTT 值列表
        acked_packets = set()        # 已确认的 seq_no (1-based)

        # ================================================================
        # 阶段 3: GBN 滑动窗口传输
        # ================================================================
        while base < TOTAL_PACKETS:
            # --- 3a. 填满发送窗口 ---
            while (next_seq < TOTAL_PACKETS and
                   bytes_in_flight + packet_sizes[next_seq] <= WINDOW_SIZE_BYTES):
                seq_no = next_seq + 1               # 1-based 序号
                pkt_size = packet_sizes[next_seq]   # 本包数据大小

                # 封装报文: Type(2B) + SeqNo(2B) + Length(2B) + Data
                header = struct.pack('!HHH', 3, seq_no, pkt_size)
                payload = b'X' * pkt_size
                client_socket.sendto(header + payload, server_addr)

                total_transmissions += 1
                send_times[seq_no] = time.time()
                bytes_in_flight += pkt_size

                print(f"第 {seq_no} 个（第 {byte_starts[next_seq]}~"
                      f"{byte_ends[next_seq]} 字节）client 端已经发送")
                log_event(
                    f"Send: 数据包 (Type=3), Seq={seq_no}, "
                    f"长度={pkt_size}B, "
                    f"字节范围={byte_starts[next_seq]}~{byte_ends[next_seq]}"
                )
                next_seq += 1

            # --- 3b. 等待 ACK 或超时 ---
            try:
                ack_data, _ = client_socket.recvfrom(4096)

                # ★ 修复点: 解析携带服务器时间的 ACK (9字节格式)
                if len(ack_data) >= 9:
                    ack_type, ack_seq, _, hour, minute, second = \
                        struct.unpack('!HHHBBB', ack_data[:9])
                elif len(ack_data) >= 6:
                    ack_type, ack_seq, _ = struct.unpack('!HHH', ack_data[:6])
                    # 兼容旧格式：用本地时间代替
                    now = datetime.datetime.now()
                    hour, minute, second = now.hour, now.minute, now.second
                else:
                    continue

                if ack_type != 4 or ack_seq <= 0:
                    continue

                server_time_str = f"{hour:02d}:{minute:02d}:{second:02d}"

                # --- 3c. 累积确认处理 ---
                newly_acked = False
                while base < TOTAL_PACKETS and (base + 1) <= ack_seq:
                    seq = base + 1
                    if seq not in acked_packets:
                        acked_packets.add(seq)
                        bytes_in_flight -= packet_sizes[base]
                        newly_acked = True

                        # 计算 RTT（使用最近一次发送时间）
                        if seq in send_times:
                            rtt_ms = (time.time() - send_times[seq]) * 1000
                            rtt_values.append(rtt_ms)

                        print(f"    --> 第 {seq} 个（第 {byte_starts[base]}~"
                              f"{byte_ends[base]} 字节）server 端已经收到，"
                              f"RTT 是 {rtt_values[-1] if rtt_values else 0:.2f} ms, "
                              f"Server时间={server_time_str}")
                        log_event(
                            f"Recv: ACK (Type=4), AckSeq={ack_seq}, "
                            f"确认第{seq}个包, "
                            f"RTT={rtt_values[-1] if rtt_values else 0:.2f}ms, "
                            f"Server时间={server_time_str}"
                        )
                    base += 1

                if not newly_acked:
                    # 重复 ACK（乱序导致），仅记录
                    log_event(
                        f"Recv: 重复 ACK, AckSeq={ack_seq}, "
                        f"当前base={base+1}(1-based)"
                    )

            except socket.timeout:
                # --- 3d. 超时 → Go-Back-N 重传 ---
                if base < TOTAL_PACKETS:
                    print(f"\n[!!!] 发生超时！未收到 ACK={base + 1}。"
                          f"开始回退 N 步重传...")
                    print(f"    --> 重传第 {base + 1} 个"
                          f"（第 {byte_starts[base]}~{byte_ends[base]} 字节）"
                          f"及后续数据包")
                    log_event(
                        f"Timeout: 超时 {TIMEOUT*1000:.0f}ms "
                        f"未收到 ACK={base+1}, "
                        f"执行 Go-Back-N 重传 (从第{base+1}个开始)"
                    )
                    # GBN: 回退窗口，重置在途字节
                    next_seq = base
                    bytes_in_flight = 0

        # ================================================================
        # 阶段 4: 传输完成，计算统计数据
        # ================================================================
        print("\n" + "-" * 55)
        print("[+] 所有 30 个包已成功被确认！传输结束。")
        log_event("传输完成: 所有30个包已被确认")

        if rtt_values:
            # ★ 修复点: 使用 pandas 计算统计量
            rtt_series = pd.Series(rtt_values, name="RTT")
            avg_rtt = rtt_series.mean()
            max_rtt = rtt_series.max()
            min_rtt = rtt_series.min()
            std_rtt = rtt_series.std()        # ★ 新增: 标准差

            # ★ 修复点: 丢包率 = 30 / 实际发送次数 × 100%
            # （这里"丢包率"按任务书要求定义为成功包数占总发送次数的比例）
            success_rate = (TOTAL_PACKETS / total_transmissions) * 100
            drop_rate = 100 - success_rate

            stats_text = (
                f"【UDP 模拟 TCP 传输统计报告】\n"
                f"{'=' * 40}\n"
                f"总计成功发送包数: {TOTAL_PACKETS}\n"
                f"实际尝试发送次数 (含重传): {total_transmissions}\n"
                f"成功送达率: {success_rate:.2f}%\n"
                f"网络丢包/重传率: {drop_rate:.2f}%\n"
                f"{'=' * 40}\n"
                f"最大 RTT: {max_rtt:.2f} ms\n"
                f"最小 RTT: {min_rtt:.2f} ms\n"
                f"平均 RTT: {avg_rtt:.2f} ms\n"
                f"RTT 标准差: {std_rtt:.2f} ms\n"
                f"{'=' * 40}\n"
                f"(统计量使用 pandas 计算)\n"
            )

            print("\n" + stats_text)

            with open("udp_statistics.txt", "w", encoding="utf-8") as f:
                f.write(stats_text)
            print("[*] 统计报告已保存至 udp_statistics.txt")

            log_event(
                f"统计报告: 发送{TOTAL_PACKETS}包/实际{total_transmissions}次, "
                f"成功送达率={success_rate:.2f}%, "
                f"avgRTT={avg_rtt:.2f}ms, stdRTT={std_rtt:.2f}ms, "
                f"minRTT={min_rtt:.2f}ms, maxRTT={max_rtt:.2f}ms"
            )
        else:
            print("[!] 警告: 未收集到任何 RTT 数据")
            log_event("警告: rtt_values 为空")

    except socket.timeout:
        print("[!] 握手超时：未收到服务器响应")
        log_event("握手超时: 未收到服务器响应")
    except Exception as e:
        print(f"发生异常: {e}")
        log_event(f"异常: {e}")
    finally:
        client_socket.close()
        log_event("客户端关闭")


if __name__ == '__main__':
    main()

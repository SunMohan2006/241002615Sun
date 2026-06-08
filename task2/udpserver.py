import socket
import struct
import sys
import random
import datetime


def log_event(msg):
    """带时间戳的日志写入 run_log.txt"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open("udp_server_run_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def main():
    if len(sys.argv) != 3:
        print("用法: python udpserver.py <ServerIP> <ServerPort>")
        sys.exit(1)

    # 每次启动时清空旧日志
    open("udp_server_run_log.txt", "w", encoding="utf-8").close()

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"[*] UDP 服务端启动，监听 {server_ip}:{server_port}")
    log_event(f"UDP 服务端启动，监听 {server_ip}:{server_port}")

    # 模拟丢包率 20%
    DROP_RATE = 0.20
    # 当前会话期望的下一个序号
    expected_seq = 1
    # 当前连接的客户端地址
    client_addr = None

    while True:
        try:
            data, addr = server_socket.recvfrom(4096)

            if len(data) < 6:
                log_event(f"收到来自 {addr} 的无效短报文 (长度={len(data)})，已忽略")
                continue

            # 解析公共首部: Type(2B) + SeqNo(2B) + Payload/Reserved(2B)
            msg_type, seq_no, payload = struct.unpack('!HHH', data[:6])

            # ============================================================
            # 握手阶段: Type = 1 (Initialization)
            # ============================================================
            if msg_type == 1:
                # 验证 StudentID: 对收到的值再次 XOR 0x5A3C，检查是否在 0~9999
                student_id = payload ^ 0x5A3C
                log_event(
                    f"Recv: 握手请求 (Type=1), 来自 {addr}, "
                    f"加密值={payload}, 解密学号={student_id}"
                )

                if 0 <= student_id <= 9999:
                    print(f"\n[+] 学号 {student_id} 验证成功，建立连接。")
                    log_event(
                        f"Send: agree 报文 (Type=2), "
                        f"学号={student_id} 验证通过"
                    )
                    # 发送 Type=2 握手确认
                    server_socket.sendto(
                        struct.pack('!HHH', 2, 0, 0), addr
                    )
                    # 重置状态，准备接收新数据
                    expected_seq = 1
                    client_addr = addr
                else:
                    # ★ 修复点: 必须打印错误信息
                    print(
                        f"\n[!] 错误: 学号验证失败！"
                        f"收到加密值={payload}, 解密结果={student_id}, "
                        f"不在合法范围 0~9999，拒绝连接。"
                    )
                    log_event(
                        f"错误: 学号验证失败，解密学号={student_id} "
                        f"(合法范围0~9999)，拒绝来自 {addr} 的连接"
                    )
                continue

            # ============================================================
            # 数据传输阶段: Type = 3 (Data Packet)
            # ============================================================
            elif msg_type == 3:
                # --- 核心机制 1: 随机丢包模拟 ---
                if random.random() < DROP_RATE:
                    print(f"[!] 模拟丢包：丢弃 Seq={seq_no}")
                    log_event(f"模拟丢包: 丢弃 Seq={seq_no} 的数据包 (无响应)")
                    continue

                now = datetime.datetime.now()
                print(f"[*] 收到数据包 Seq={seq_no}, 数据长度={payload}")
                log_event(
                    f"Recv: 数据包 (Type=3), Seq={seq_no}, "
                    f"数据长度={payload}, 来自 {addr}"
                )

                # --- 核心机制 2: GBN 累积确认 ---
                if seq_no == expected_seq:
                    print(f"    --> 序号正确，发送 ACK={seq_no}")
                    # ★ 修复点: ACK 中携带服务器系统时间 (hh:mm:ss)
                    ack_packet = struct.pack(
                        '!HHHBBB',
                        4,                  # Type=4 (ACK)
                        seq_no,             # 确认的序号
                        0,                  # Reserved
                        now.hour,           # 服务器时间-时
                        now.minute,         # 服务器时间-分
                        now.second          # 服务器时间-秒
                    )
                    server_socket.sendto(ack_packet, addr)
                    log_event(
                        f"Send: ACK (Type=4), AckSeq={seq_no}, "
                        f"服务器时间={now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                    )
                    expected_seq += 1
                else:
                    # 乱序包: 重传最近一次正确接收的 ACK
                    ack_seq = expected_seq - 1
                    print(
                        f"    --> 乱序包！期望 {expected_seq}，"
                        f"实际收到 {seq_no}。重传上一次的 ACK={ack_seq}"
                    )
                    log_event(
                        f"乱序包: 期望Seq={expected_seq}, "
                        f"实际Seq={seq_no}, 重传ACK={ack_seq}"
                    )
                    if ack_seq > 0:
                        ack_packet = struct.pack(
                            '!HHHBBB',
                            4, ack_seq, 0,
                            now.hour, now.minute, now.second
                        )
                        server_socket.sendto(ack_packet, addr)
                    else:
                        log_event("警告: 收到乱序包但无可确认的包 (ack_seq=0)")

        except KeyboardInterrupt:
            print("\n[*] 服务端关闭")
            log_event("服务端手动关闭 (KeyboardInterrupt)")
            break
        except Exception as e:
            log_event(f"异常: {e}")
            print(f"[!] 异常: {e}")

    server_socket.close()


if __name__ == '__main__':
    main()

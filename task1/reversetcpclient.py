import socket
import struct
import sys
import random
import datetime


def log_event(msg):
    """带时间戳的日志写入 client_run_log.txt"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open("client_run_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def generate_chunks(total_length, lmin, lmax, seed=None):
    """
    分块算法:
      在 [lmin, lmax] 范围内随机生成每块长度，
      最后一块取剩余长度（可能小于 lmin）。
    参数 seed 用于固定随机种子，确保分块可复现。
    返回: (chunk_sizes: list, n_chunks: int)
    """
    if seed is not None:
        random.seed(seed)

    chunk_sizes = []
    current_len = 0

    while current_len < total_length:
        chunk_size = min(random.randint(lmin, lmax),
                         total_length - current_len)
        chunk_sizes.append(chunk_size)
        current_len += chunk_size

    return chunk_sizes, len(chunk_sizes)


def main():
    # ★ 修复点: 新增可选的 Seed 参数
    if len(sys.argv) < 5 or len(sys.argv) > 6:
        print("用法: python reversetcpclient.py <IP> <Port> <Lmin> <Lmax> [Seed]")
        print("  Seed: 可选，随机种子，用于复现分块结果（验收需要）")
        sys.exit(1)

    # 每次启动客户端时，清空旧日志和旧输出文件
    open("client_run_log.txt", "w", encoding="utf-8").close()
    open("reversed_output.txt", "w", encoding="utf-8").close()

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    lmin = int(sys.argv[3])
    lmax = int(sys.argv[4])
    seed = int(sys.argv[5]) if len(sys.argv) == 6 else None

    # 构造待发送的 ASCII 文件内容
    file_content = b"a little monkey is jumping on the tree."
    total_length = len(file_content)

    # ★ 修复点: 使用可复现的分块算法
    chunk_sizes, n_chunks = generate_chunks(total_length, lmin, lmax, seed)

    # 在日志中记录分块信息（便于验收时核对）
    log_event(
        f"分块参数: 文件总长={total_length}B, Lmin={lmin}, Lmax={lmax}, "
        f"Seed={seed if seed is not None else '无(随机)'}, "
        f"N={n_chunks}, 各块长度={chunk_sizes}"
    )
    print(f"[*] 文件总长={total_length}B, N={n_chunks}块, "
          f"各块长度={chunk_sizes}")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, server_port))

        # ---- 1. 发送 Type=1 Initialization ----
        client_socket.sendall(struct.pack('!HI', 1, n_chunks))
        log_event(f"Send: Initialization 报文 (Type=1), 请求块数 N={n_chunks}")

        # ---- 2. 接收 Type=2 agree ----
        agree_data = client_socket.recv(2)
        msg_type, = struct.unpack('!H', agree_data)

        if msg_type == 2:
            log_event("Recv: agree 报文 (Type=2)")
            print(f"[*] 握手成功, 准备发送 {n_chunks} 块数据...\n" + "-" * 50)

            start_idx = 0
            final_reversed_text = ""

            # ---- 3. 循环: 发送 Type=3 并接收 Type=4 ----
            for i, chunk_size in enumerate(chunk_sizes):
                chunk_data = file_content[start_idx:start_idx + chunk_size]
                start_idx += chunk_size

                # 发送 reverseRequest
                req_header = struct.pack('!HI', 3, chunk_size)
                client_socket.sendall(req_header + chunk_data)
                log_event(
                    f"Send: reverseRequest 报文 (Type=3), "
                    f"第 {i+1} 块, 长度={chunk_size}"
                )

                # 接收 reverseAnswer
                ans_header = client_socket.recv(6)
                ans_type, ans_length = struct.unpack('!HI', ans_header)

                if ans_type == 4:
                    reversed_data = client_socket.recv(ans_length)
                    log_event(
                        f"Recv: reverseAnswer 报文 (Type=4), "
                        f"第 {i+1} 块, 长度={ans_length}"
                    )

                    decoded_text = reversed_data.decode('ascii')
                    # ★ 修复点: 打印格式更接近要求示例
                    # 要求示例: "8: yeknom elttil a."
                    print(f"{i+1}: {decoded_text}")

                    # 全局倒序：新收到的块拼在前面
                    final_reversed_text = decoded_text + final_reversed_text

            # ---- 4. 写入最终反转结果 ----
            with open("reversed_output.txt", "w", encoding="utf-8") as out_f:
                out_f.write(final_reversed_text)

            print("-" * 50)
            print(f"\n[*] 数据交互完成，共 {n_chunks} 块，"
                  f"结果已保存至 reversed_output.txt")
            log_event(f"传输完成: 共 {n_chunks} 块, 反转文本已保存")

    except Exception as e:
        print(f"异常: {e}")
        log_event(f"异常: {e}")
    finally:
        client_socket.close()


if __name__ == '__main__':
    main()

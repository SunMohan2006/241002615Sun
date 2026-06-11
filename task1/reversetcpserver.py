import socket
import struct
import threading
import sys
import datetime


# 全局连接计数器（用于展示多客户端并发处理）
active_connections = 0
lock = threading.Lock()


def log_event(msg):
    """带时间戳的日志写入 server_run_log.txt"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open("server_run_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def recv_exact(conn, n_bytes):
    """确保收满 n_bytes 个字节（处理 TCP 分包）"""
    data = b''
    while len(data) < n_bytes:
        chunk = conn.recv(n_bytes - len(data))
        if not chunk:
            raise ConnectionError("客户端意外断开连接")
        data += chunk
    return data


def handle_client(conn, addr):
    """处理单个客户端请求的线程函数"""
    global active_connections
    with lock:
        active_connections += 1
        conn_id = active_connections

    print(f"[+] 客户端 #{conn_id} {addr} 已接入 (当前活跃: {active_connections})")
    log_event(f"客户端 #{conn_id} {addr} 已接入 (活跃连接数: {active_connections})")

    try:
        # ---- 1. 接收 Type=1 Initialization (6 字节) ----
        init_data = recv_exact(conn, 6)
        msg_type, n_chunks = struct.unpack('!HI', init_data)

        if msg_type != 1:
            log_event(f"客户端 #{conn_id}: 期望 Type=1，收到 Type={msg_type}，断开")
            return

        log_event(f"Recv: Initialization 报文 (Type=1), 来自 #{conn_id} {addr}, N={n_chunks}")

        # ---- 2. 发送 Type=2 agree ----
        conn.sendall(struct.pack('!H', 2))
        log_event(f"Send: agree 报文 (Type=2), 发往 #{conn_id} {addr}")

        # ---- 3. 循环处理每块数据 ----
        for i in range(n_chunks):
            # 接收 reverseRequest 头部 (6 字节)
            header_data = recv_exact(conn, 6)
            req_type, data_length = struct.unpack('!HI', header_data)

            if req_type != 3:
                log_event(f"客户端 #{conn_id}: 期望 Type=3，收到 Type={req_type}")
                break

            # 接收请求数据
            raw_data = recv_exact(conn, data_length)
            log_event(f"Recv: reverseRequest 报文 (Type=3), "
                      f"第 {i+1}/{n_chunks} 块, 长度={data_length}")

            # 反转数据
            reversed_data = raw_data[::-1]

            # 发送 reverseAnswer
            ans_header = struct.pack('!HI', 4, data_length)
            conn.sendall(ans_header + reversed_data)
            log_event(f"Send: reverseAnswer 报文 (Type=4), "
                      f"第 {i+1}/{n_chunks} 块, 长度={data_length}")

        print(f"[{addr}] #{conn_id} 处理完毕")
        log_event(f"客户端 #{conn_id} {addr} 处理完毕")

    except ConnectionError as e:
        log_event(f"客户端 #{conn_id} {addr} 连接异常: {e}")
        print(f"[{addr}] #{conn_id} 连接断开: {e}")
    except Exception as e:
        log_event(f"客户端 #{conn_id} {addr} 异常: {e}")
        print(f"[{addr}] #{conn_id} 异常: {e}")
    finally:
        conn.close()
        with lock:
            active_connections -= 1
        log_event(f"客户端 #{conn_id} {addr} 断开 (活跃连接数: {active_connections})")


def main():
    if len(sys.argv) != 3:
        print("用法: python reversetcpserver.py <IP> <Port>")
        sys.exit(1)

    # 每次启动时清空旧日志
    open("server_run_log.txt", "w", encoding="utf-8").close()

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)

    print(f"[*] 服务端启动 {server_ip}:{server_port} (最大等待队列: 5)")
    log_event(f"服务端启动 {server_ip}:{server_port}")

    try:
        while True:
            conn, addr = server_socket.accept()
            #  多线程支持: 每个客户端独立线程处理
            client_thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[*] 服务端手动关闭")
        log_event("服务端手动关闭 (KeyboardInterrupt)")
    finally:
        server_socket.close()
        log_event("服务端 socket 关闭")


if __name__ == '__main__':
    main()

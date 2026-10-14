"""
seed_questions.py - Nạp dữ liệu mẫu ban đầu cho Ngân hàng câu hỏi
Chủ đề: Mạng Máy Tính, Lập Trình Mạng & Kiến Trúc Giao Thức (Môn Lập Trình Mạng)
Phân loại rõ ràng: Dễ (easy), Trung bình (medium), Khó (hard)
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from database import init_db, get_connection

SAMPLE_QUESTIONS = [
    # ===== DỄ (EASY) =====
    {
        "content": "Mô hình OSI (Open Systems Interconnection) có bao nhiêu tầng?",
        "option_a": "4 tầng",
        "option_b": "5 tầng",
        "option_c": "7 tầng",
        "option_d": "6 tầng",
        "correct_answer": "C",
        "difficulty": "easy",
        "category": "Mô hình OSI & TCP/IP",
        "explanation": "Mô hình OSI gồm 7 tầng chuẩn: Vật lý, Liên kết dữ liệu, Mạng, Giao vận, Phiên, Trình diễn và Ứng dụng."
    },
    {
        "content": "Giao thức nào sau đây hoạt động ở tầng Giao vận (Transport Layer) và cung cấp dịch vụ tin cậy, có kết nối?",
        "option_a": "UDP",
        "option_b": "TCP",
        "option_c": "IP",
        "option_d": "ICMP",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Giao thức Mạng",
        "explanation": "TCP (Transmission Control Protocol) là giao thức hướng kết nối, đảm bảo truyền dữ liệu tin cậy, kiểm soát lỗi và luồng dữ liệu."
    },
    {
        "content": "Cổng mặc định (Default Port) của giao thức HTTP là bao nhiêu?",
        "option_a": "21",
        "option_b": "80",
        "option_c": "443",
        "option_d": "8080",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Giao thức Ứng dụng",
        "explanation": "HTTP sử dụng cổng mặc định là 80, trong khi HTTPS sử dụng cổng 443."
    },
    {
        "content": "Cổng mặc định (Default Port) của giao thức HTTPS (bảo mật) là cổng nào?",
        "option_a": "80",
        "option_b": "22",
        "option_c": "443",
        "option_d": "25",
        "correct_answer": "C",
        "difficulty": "easy",
        "category": "Giao thức Ứng dụng",
        "explanation": "HTTPS mã hoá dữ liệu qua SSL/TLS và sử dụng cổng TCP chuẩn 443."
    },
    {
        "content": "Địa chỉ IPv4 chuẩn có độ dài bao nhiêu bit?",
        "option_a": "32 bit",
        "option_b": "64 bit",
        "option_c": "128 bit",
        "option_d": "16 bit",
        "correct_answer": "A",
        "difficulty": "easy",
        "category": "Địa chỉ IP",
        "explanation": "Địa chỉ IPv4 gồm 32 bit, được chia thành 4 octet cách nhau bởi dấu chấm."
    },
    {
        "content": "Địa chỉ IPv6 chuẩn có độ dài bao nhiêu bit?",
        "option_a": "32 bit",
        "option_b": "64 bit",
        "option_c": "128 bit",
        "option_d": "256 bit",
        "correct_answer": "C",
        "difficulty": "easy",
        "category": "Địa chỉ IP",
        "explanation": "Địa chỉ IPv6 được thiết kế với độ dài 128 bit để mở rộng không gian địa chỉ toàn cầu."
    },
    {
        "content": "Giao thức nào có nhiệm vụ phân giải tên miền (Domain Name) thành địa chỉ IP?",
        "option_a": "DHCP",
        "option_b": "DNS",
        "option_c": "ARP",
        "option_d": "FTP",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Giao thức Ứng dụng",
        "explanation": "DNS (Domain Name System) chuyển đổi tên miền thân thiện (ví dụ google.com) sang địa chỉ IP máy chủ."
    },
    {
        "content": "Địa chỉ IP nào sau đây là địa chỉ Loopback (Localhost)?",
        "option_a": "192.168.1.1",
        "option_b": "10.0.0.1",
        "option_c": "127.0.0.1",
        "option_d": "255.255.255.255",
        "correct_answer": "C",
        "difficulty": "easy",
        "category": "Địa chỉ IP",
        "explanation": "127.0.0.1 là địa chỉ loopback tiêu chuẩn dùng để máy tính tự giao tiếp với chính nó qua ngăn xếp mạng."
    },
    {
        "content": "Giao thức UDP khác TCP ở đặc điểm cơ bản nào sau đây?",
        "option_a": "UDP có kết nối và đảm bảo không mất gói tin",
        "option_b": "UDP không kết nối (connectionless) và tốc độ nhanh hơn",
        "option_c": "UDP chỉ truyền được dữ liệu văn bản",
        "option_d": "UDP hoạt động ở tầng Ứng dụng",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Giao thức Mạng",
        "explanation": "UDP là giao thức không hướng kết nối, không có cơ chế bắt tay 3 bước, giảm thiểu trễ và phù hợp với streaming, gaming."
    },
    {
        "content": "Giao thức nào tự động cấp phát địa chỉ IP động cho các thiết bị trong mạng LAN?",
        "option_a": "DNS",
        "option_b": "DHCP",
        "option_c": "SNMP",
        "option_d": "SMTP",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Giao thức Mạng",
        "explanation": "DHCP (Dynamic Host Configuration Protocol) tự động gán địa chỉ IP, Subnet Mask và Gateway cho client."
    },
    {
        "content": "Lệnh dòng lệnh nào dùng để kiểm tra tính thông suốt và độ trễ tới một địa chỉ mạng?",
        "option_a": "tracert",
        "option_b": "ping",
        "option_c": "ipconfig",
        "option_d": "netstat",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Công cụ Mạng",
        "explanation": "Lệnh 'ping' sử dụng các gói tin ICMP Echo Request/Reply để đo lường độ trễ (RTT) và kiểm tra kết nối."
    },
    {
        "content": "Địa chỉ MAC (Media Access Control) có độ dài chuẩn là bao nhiêu bit?",
        "option_a": "32 bit",
        "option_b": "48 bit",
        "option_c": "64 bit",
        "option_d": "128 bit",
        "correct_answer": "B",
        "difficulty": "easy",
        "category": "Tầng Liên kết dữ liệu",
        "explanation": "Địa chỉ MAC là địa chỉ vật lý của card mạng NIC, dài 48 bit (6 byte), biểu diễn bằng hệ Hexadecimal."
    },

    # ===== TRUNG BÌNH (MEDIUM) =====
    {
        "content": "Trong quá trình thiết lập kết nối TCP, quá trình bắt tay 3 bước (3-way handshake) diễn ra theo thứ tự các cờ (flags) nào?",
        "option_a": "ACK -> SYN -> SYN-ACK",
        "option_b": "SYN -> SYN-ACK -> ACK",
        "option_c": "SYN -> ACK -> FIN",
        "option_d": "RST -> SYN -> ACK",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Lập trình Socket & TCP",
        "explanation": "Client gửi gói SYN; Server phản hồi SYN-ACK; Client gửi lại ACK hoàn tất thiết lập kênh truyền tin cậy."
    },
    {
        "content": "Trong lập trình Socket trên hệ điều hành, hàm nào được gọi phía Server để liên kết một socket với một địa chỉ IP và Port cụ thể?",
        "option_a": "listen()",
        "option_b": "bind()",
        "option_c": "connect()",
        "option_d": "accept()",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Lập trình Socket",
        "explanation": "Hàm bind() gắn kết (binds) socket descriptor với cấu trúc địa chỉ mạng sockaddr gồm IP và Port."
    },
    {
        "content": "Trong lập trình TCP Socket phía Server, hàm accept() có vai trò gì?",
        "option_a": "Chấp nhận gói tin dữ liệu gửi đến socket",
        "option_b": "Lắng nghe các yêu cầu kết nối trên cổng",
        "option_c": "Chấp nhận một kết nối mới và trả về một socket riêng để trao đổi dữ liệu với client đó",
        "option_d": "Đóng kết nối của client khi kết thúc",
        "correct_answer": "C",
        "difficulty": "medium",
        "category": "Lập trình Socket",
        "explanation": "accept() lấy yêu cầu kết nối đầu tiên trong hàng đợi lắng nghe và tạo một socket mới dành riêng cho kết nối đó."
    },
    {
        "content": "Subnet Mask /26 tương ứng với dạng thập phân (dotted-decimal) nào sau đây?",
        "option_a": "255.255.255.128",
        "option_b": "255.255.255.192",
        "option_c": "255.255.255.224",
        "option_d": "255.255.255.240",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Địa chỉ IP & Subnetting",
        "explanation": "Octet cuối cùng của /26 có 2 bit 1: 128 + 64 = 192. Do đó Subnet Mask là 255.255.255.192."
    },
    {
        "content": "Trong một mạng con có tiền tố /28, có tối đa bao nhiêu địa chỉ IP khả dụng cho các thiết bị (host)?",
        "option_a": "16",
        "option_b": "14",
        "option_c": "30",
        "option_d": "6",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Địa chỉ IP & Subnetting",
        "explanation": "Số bit host là 32 - 28 = 4 bit. Số địa chỉ = 2^4 = 16. Trừ 2 địa chỉ mạng và broadcast -> Còn 14 địa chỉ host khả dụng."
    },
    {
        "content": "Giao thức ARP (Address Resolution Protocol) dùng để làm gì?",
        "option_a": "Tìm địa chỉ IP khi biết địa chỉ MAC",
        "option_b": "Tìm địa chỉ MAC khi biết địa chỉ IP trong mạng cục bộ",
        "option_c": "Định tuyến gói tin qua Internet",
        "option_d": "Mã hóa địa chỉ IP qua VPN",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Giao thức Mạng",
        "explanation": "ARP gửi gói tin broadcast trong mạng LAN để hỏi thiết bị có IP tương ứng gửi lại địa chỉ vật lý MAC."
    },
    {
        "content": "Công nghệ WebSocket khác biệt như thế nào so với HTTP thông thường?",
        "option_a": "WebSocket chỉ hoạt động trên mạng nội bộ",
        "option_b": "WebSocket cung cấp kênh truyền 2 chiều toàn song công (full-duplex) liên tục qua 1 kết nối TCP duy nhất",
        "option_c": "WebSocket gửi yêu cầu độc lập và đóng kết nối ngay sau mỗi phản hồi",
        "option_d": "WebSocket sử dụng UDP thay vì TCP",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Lập trình Mạng Nâng cao",
        "explanation": "WebSocket nâng cấp từ HTTP (handshake), duy trì kênh kết nối 2 chiều liên tục (full-duplex) với độ trễ tối thiểu."
    },
    {
        "content": "Mã trạng thái HTTP nào sau đây đại diện cho 'Internal Server Error' (Lỗi máy chủ nội bộ)?",
        "option_a": "400",
        "option_b": "404",
        "option_c": "500",
        "option_d": "502",
        "correct_answer": "C",
        "difficulty": "medium",
        "category": "Giao thức Ứng dụng",
        "explanation": "Nhóm mã 5xx biểu thị lỗi từ phía máy chủ; trong đó 500 là Internal Server Error."
    },
    {
        "content": "Kỹ thuật Non-blocking I/O hoặc Asynchronous I/O (async/await, epoll, select) trong server mạng nhằm giải quyết vấn đề gì?",
        "option_a": "Tự động mã hóa lưu lượng mạng",
        "option_b": "Xử lý hàng nghìn kết nối đồng thời (concurrency) mà không cần tạo 1 thread nặng nề cho mỗi client (vấn đề C10K)",
        "option_c": "Tăng băng thông phần cứng của cáp mạng",
        "option_d": "Bỏ qua lớp kiểm tra bảo mật tường lửa",
        "correct_answer": "B",
        "difficulty": "medium",
        "category": "Lập trình Socket",
        "explanation": "Async/Non-blocking I/O cho phép một luồng sự kiện (event loop) phục vụ nhiều socket cùng lúc khi dữ liệu sẵn sàng."
    },
    {
        "content": "Cơ chế kiểm soát luồng (Flow Control) trong giao thức TCP được thực hiện thông qua cơ chế nào?",
        "option_a": "Cửa sổ trượt (Sliding Window)",
        "option_b": "Khóa mutex",
        "option_c": "Thuật toán Bellman-Ford",
        "option_d": "Mã sửa sai Hamming",
        "correct_answer": "A",
        "difficulty": "medium",
        "category": "Giao thức Mạng",
        "explanation": "TCP sử dụng trường Window Size trong TCP Header để thông báo khả năng tiếp nhận bộ đệm của bên nhận (Sliding Window)."
    },

    # ===== KHÓ (HARD) =====
    {
        "content": "Trong quá trình đóng kết nối TCP (4-way termination), trạng thái TIME_WAIT ở bên chủ động đóng nhằm mục đích gì?",
        "option_a": "Đợi server khởi động lại",
        "option_b": "Đảm bảo gói tin ACK cuối cùng đến đích và ngăn các gói tin cũ của kết nối này gây nhầm lẫn cho kết nối mới",
        "option_c": "Giải phóng ngay bộ nhớ RAM của hệ điều hành",
        "option_d": "Mã hóa lại dữ liệu trước khi ngắt",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "Lập trình Socket & TCP",
        "explanation": "TIME_WAIT kéo dài 2*MSL (Maximum Segment Lifetime) để đảm bảo ACK cuối đến được phía kia, nếu mất ACK thì kịp gửi lại trước khi port được tái sử dụng."
    },
    {
        "content": "Thuật toán điều khiển tắc nghẽn (Congestion Control) cổ điển của TCP (như TCP Reno/Tahoe) gồm các giai đoạn nào theo trình tự?",
        "option_a": "Fast Retransmit -> Slow Start -> Stop and Wait",
        "option_b": "Slow Start (Khởi đầu chậm) -> Congestion Avoidance (Tránh tắc nghẽn) -> Fast Retransmit / Fast Recovery",
        "option_c": "Round Robin -> Priority Queue -> Token Bucket",
        "option_d": "Selective Repeat -> Go-Back-N -> Stop",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "Giao thức Mạng",
        "explanation": "TCP bắt đầu từ Slow Start (tăng cwnd theo hàm mũ), khi đạt ssthresh chuyển sang Congestion Avoidance (tăng tuyến tính), và kích hoạt Fast Recovery khi nhận 3 DUP ACK."
    },
    {
        "content": "Trong lập trình Socket, hiện tượng 'TCP Segmentation / Packet Framing' (hoặc Sticky Packets) có nghĩa là gì?",
        "option_a": "Các gói tin TCP luôn có kích thước cố định 512 bytes",
        "option_b": "TCP là byte stream không có ranh giới tin nhắn (message boundary), dữ liệu của 2 lệnh send() có thể dính vào nhau hoặc bị phân mảnh trong 1 lệnh recv()",
        "option_c": "Gói tin TCP bị kẹt ở card mạng do lỗi phần cứng",
        "option_d": "Giao thức TCP tự động chèn ký tự xuống dòng '\\n' vào cuối mỗi frame",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "Lập trình Socket",
        "explanation": "Vì TCP là giao thức truyền chuỗi byte liên tục (stream-oriented), ứng dụng phải tự định nghĩa giao thức tầng trên (như độ dài tiền tố Length-prefixed hoặc delimiter như '\\r\\n') để tách thông điệp."
    },
    {
        "content": "Tùy chọn Socket 'SO_REUSEADDR' thường được đặt trước hàm bind() nhằm giải quyết vấn đề gì?",
        "option_a": "Tự động phân phát địa chỉ IP qua DHCP",
        "option_b": "Cho phép bind lại ngay vào cổng vừa đóng dù socket cũ còn ở trạng thái TIME_WAIT ('Address already in use')",
        "option_c": "Tăng tốc độ truyền tải lên gấp đôi",
        "option_d": "Cho phép hai server khác nhau cùng nhận dữ liệu trên 1 port",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "Lập trình Socket",
        "explanation": "Khi restart server, cổng có thể vẫn ở trạng thái TIME_WAIT gây lỗi 'Address already in use'. SO_REUSEADDR cho phép tái sử dụng địa chỉ/cổng này ngay lập tức."
    },
    {
        "content": "Mạng 172.16.0.0/16 được chia thành các mạng con có kích thước /22. Có tối đa bao nhiêu mạng con và mỗi mạng con có bao nhiêu địa chỉ IP khả dụng cho host?",
        "option_a": "64 mạng con, mỗi mạng 1022 host khả dụng",
        "option_b": "32 mạng con, mỗi mạng 2046 host khả dụng",
        "option_c": "128 mạng con, mỗi mạng 510 host khả dụng",
        "option_d": "16 mạng con, mỗi mạng 4094 host khả dụng",
        "correct_answer": "A",
        "difficulty": "hard",
        "category": "Địa chỉ IP & Subnetting",
        "explanation": "Số bit mượn subnet: 22 - 16 = 6 bit -> Số mạng con = 2^6 = 64. Số bit host: 32 - 22 = 10 bit -> Số host khả dụng = 2^10 - 2 = 1024 - 2 = 1022."
    },
    {
        "content": "Giao thức BGP (Border Gateway Protocol) dùng trong định tuyến Internet liên vùng (Inter-domain) thuộc loại giao thức nào?",
        "option_a": "Link-State Routing Protocol",
        "option_b": "Distance-Vector Routing Protocol thuần túy",
        "option_c": "Path-Vector Routing Protocol",
        "option_d": "Interior Gateway Protocol",
        "correct_answer": "C",
        "difficulty": "hard",
        "category": "Định tuyến Mạng",
        "explanation": "BGP là giao thức Path-Vector, lưu giữ toàn bộ đường dẫn các AS (Autonomous Systems) đi qua (AS-Path) để ngăn ngừa vòng lặp định tuyến (routing loop)."
    },
    {
        "content": "Trong lập trình mạng đa luồng (Multi-threaded Server), mô hình 'Thread Pool' mang lại ưu điểm vượt trội nào so với mô hình 'Thread-per-connection'?",
        "option_a": "Không cần sử dụng bộ đệm mạng",
        "option_b": "Hạn chế chi phí tạo/hủy thread liên tục và giới hạn số lượng luồng tối đa để tránh cạn kiệt tài nguyên bộ nhớ hệ thống",
        "option_c": "Tự động chuyển đổi TCP sang UDP khi nghẽn mạng",
        "option_d": "Không cần đồng bộ hóa dữ liệu dùng chung",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "Kiến trúc Server Mạng",
        "explanation": "Thread-per-connection sẽ làm sụp đổ server khi có hàng nghìn kết nối do chi phí chuyển ngữ cảnh (context switch) và stack memory. Thread Pool duy trì số lượng worker ổn định."
    },
    {
        "content": "Tấn công SYN Flood khai thác điểm yếu nào trong giao thức TCP?",
        "option_a": "Lỗ hổng tràn bộ đệm trong hàm send()",
        "option_b": "Hàng đợi nửa mở (Half-open / SYN queue) của server bị lấp đầy do kẻ tấn công gửi liên tục SYN mà không gửi lại ACK hoàn tất bắt tay",
        "option_c": "Giải mã khóa bí mật SSL/TLS",
        "option_d": "Giả mạo bảng định tuyến ARP",
        "correct_answer": "B",
        "difficulty": "hard",
        "category": "An toàn Mạng",
        "explanation": "Kẻ tấn công gửi nhiều gói SYN với IP giả mạo. Server cấp phát bộ nhớ và đợi ACK trong SYN queue cho đến khi cạn kiệt tài nguyên không thể phục vụ client hợp lệ."
    }
]

def seed_database():
    """Chạy khởi tạo CSDL và nạp bộ câu hỏi mẫu"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]

    if count == 0:
        print(f"Đang nạp {len(SAMPLE_QUESTIONS)} câu hỏi mẫu vào CSDL...")
        for q in SAMPLE_QUESTIONS:
            cursor.execute("""
                INSERT INTO questions (content, option_a, option_b, option_c, option_d, correct_answer, difficulty, category, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q["content"], q["option_a"], q["option_b"], q["option_c"], q["option_d"],
                q["correct_answer"], q["difficulty"], q["category"], q["explanation"]
            ))
        conn.commit()
        print("Đã nạp câu hỏi mẫu thành công!")
    else:
        print(f"Cơ sở dữ liệu đã có {count} câu hỏi, bỏ qua nạp mới.")

    conn.close()

if __name__ == "__main__":
    seed_database()

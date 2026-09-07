#include "TelemetrySender.h"

#include <cstring>
#include <utility>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using SocketHandle = SOCKET;
constexpr SocketHandle kInvalidSocket = INVALID_SOCKET;
void closeSocket(SocketHandle socket) { closesocket(socket); }
#else
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>
using SocketHandle = int;
constexpr SocketHandle kInvalidSocket = -1;
void closeSocket(SocketHandle socket) { close(socket); }
#endif

TcpTelemetrySender::TcpTelemetrySender(std::string host, int port)
    : host_(std::move(host)), port_(port) {}

bool TcpTelemetrySender::send(const std::string& message) {
#ifdef _WIN32
    WSADATA winsockData{};
    if (WSAStartup(MAKEWORD(2, 2), &winsockData) != 0) {
        return false;
    }
#endif

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* addresses = nullptr;
    const std::string port = std::to_string(port_);
    if (getaddrinfo(host_.c_str(), port.c_str(), &hints, &addresses) != 0) {
#ifdef _WIN32
        WSACleanup();
#endif
        return false;
    }

    SocketHandle connectedSocket = kInvalidSocket;
    for (addrinfo* address = addresses; address != nullptr; address = address->ai_next) {
        SocketHandle candidate = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
        if (candidate == kInvalidSocket) {
            continue;
        }
        if (connect(candidate, address->ai_addr, static_cast<int>(address->ai_addrlen)) == 0) {
            connectedSocket = candidate;
            break;
        }
        closeSocket(candidate);
    }
    freeaddrinfo(addresses);

    bool success = connectedSocket != kInvalidSocket;
    if (success) {
        const std::string framed = message + "\n";
        std::size_t sentTotal = 0;
        while (sentTotal < framed.size()) {
            const auto sent = ::send(
                connectedSocket,
                framed.data() + sentTotal,
                static_cast<int>(framed.size() - sentTotal),
                0);
            if (sent <= 0) {
                success = false;
                break;
            }
            sentTotal += static_cast<std::size_t>(sent);
        }
        closeSocket(connectedSocket);
    }

#ifdef _WIN32
    WSACleanup();
#endif
    return success;
}

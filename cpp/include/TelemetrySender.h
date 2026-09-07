#pragma once

#include <string>

class ITelemetrySender {
public:
    virtual ~ITelemetrySender() = default;
    virtual bool send(const std::string& message) = 0;
};

class TcpTelemetrySender final : public ITelemetrySender {
public:
    TcpTelemetrySender(std::string host, int port);
    bool send(const std::string& message) override;

private:
    std::string host_;
    int port_;
};

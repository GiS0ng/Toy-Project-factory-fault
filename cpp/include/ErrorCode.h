#ifndef ERROR_CODE_H
#define ERROR_CODE_H

enum ErrorCode {
    ISO_NORMAL = 0,    // Grade A/B (0~399)
    ISO_WARNING = 1,   // Grade C (400~599)
    ISO_CRITICAL = 2   // Grade D (600~800)
};

#endif
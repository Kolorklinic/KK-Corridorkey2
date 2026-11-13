// ---------------------------------------------------------------------------
// CorridorKey 2 for Resolve - runs the Python worker and follows its progress
//
// From Creative Video Tips (CVT)  |  https://creativevideotips.com
// Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
// ---------------------------------------------------------------------------
#pragma once

#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <sys/types.h>

namespace ck2 {

struct JobUpdate {
    std::string status;     // one line for the Status field
    bool finished = false;  // the worker has exited
    bool ok = false;        // finished and wrote every frame
};

class Job : public std::enable_shared_from_this<Job> {
public:
    using Callback = std::function<void(const JobUpdate&)>;

    // Starts `python -u worker run job` with stdout read here and stderr
    // appended to `logPath`. No shell is involved. Returns null and sets
    // `error` if the process can't be started.
    static std::shared_ptr<Job> start(const std::string& python, const std::string& worker,
                                      const std::string& jobPath, const std::string& logPath,
                                      Callback onUpdate, std::string& error);

    bool running() const;
    void cancel();          // stops the worker
    void detach();          // no more callbacks (the node is going away)

private:
    void readLoop(int fd);
    void report(const JobUpdate& u);

    mutable std::mutex mutex_;
    Callback callback_;
    pid_t pid_ = -1;
    bool running_ = false;
    bool cancelled_ = false;
};

}  // namespace ck2

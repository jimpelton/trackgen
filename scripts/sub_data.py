#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

import zmq

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://localhost:5557")
sub.subscribe(b"telemetry")
while True:
    print(sub.recv_string())

import zmq

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://localhost:5556")
sub.subscribe(b"drone")
while True:
    print(sub.recv_string())

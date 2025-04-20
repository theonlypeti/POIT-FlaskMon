from threading import Lock
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import itertools
from multiprocessing import Pool, cpu_count
from math import sqrt
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Global variables for prime finding
prime_pool = None
is_finding_primes = False
primes_found = []
thread_lock = Lock()


def is_prime(n):
    if n < 2:
        return 0
    if n == 2:
        return n
    if n % 2 == 0:
        return 0
    for i in range(3, int(sqrt(n)) + 1, 2):
        if n % i == 0:
            return 0
    return n


def prime_finder_thread(processes=None):
    global prime_pool, is_finding_primes, primes_found

    numgen = itertools.count(100000000001, 2)
    print(f"37{processes=}")
    cpus = processes or cpu_count()
    print(f"39{cpus=}")
    primes_found = []

    try:
        with Pool(processes=cpus) as pool:
            prime_pool = pool
            is_finding_primes = True

            for result in pool.imap_unordered(is_prime, numgen, chunksize=1000):
                if not is_finding_primes:
                    break

                if result:
                    primes_found.append(result)
                    socketio.emit('prime_found',
                                  {'prime': result, 'count': len(primes_found)},
                                  namespace='/test')
    except Exception as e:
        socketio.emit('error', {'message': str(e)}, namespace='/test')
    finally:
        is_finding_primes = False
        prime_pool = None
        socketio.emit('prime_status',
                      {'status': 'stopped', 'count': len(primes_found)},
                      namespace='/test')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/graphlive')
def graphlive():
    return render_template('graphlive.html')


@app.route('/primes')
def primes_page():
    return render_template('primes.html')


@app.route('/api/start_primes', methods=['POST'])
def start_primes():
    global is_finding_primes

    if is_finding_primes:
        return jsonify({'status': 'already_running'})

    processes = request.json.get('processes') if request.json else None
    print(f"89{processes=}")
    if processes:
        processes = max(1, int(processes))
    print(f"92{processes=}")

    socketio.start_background_task(prime_finder_thread, processes)
    return jsonify({'status': 'started', 'processes': processes or cpu_count()})


@app.route('/api/stop_primes', methods=['POST'])
def stop_primes():
    global prime_pool, is_finding_primes

    if not is_finding_primes:
        return jsonify({'status': 'not_running'})

    is_finding_primes = False
    if prime_pool:
        prime_pool.terminate()
        prime_pool.join()

    return jsonify({'status': 'stopped', 'primes_found': len(primes_found)})


@socketio.on('start_primes', namespace='/test')
def socket_start_primes(*args, **kwargs):
    global is_finding_primes

    if is_finding_primes:
        emit('prime_status', {'status': 'already_running'})
        return

    # Get processes from arguments or use None to default to CPU count
    processes = None

    print("124", args)
    if args and isinstance(args[0], dict) and 'processes' in args[0]:
        processes = max(1, int(args[0]['processes']))  # Ensure at least 1

    print(f"127{processes=}")

    socketio.start_background_task(prime_finder_thread, processes)
    emit('prime_status', {'status': 'started', 'processes': processes or cpu_count()})


@socketio.on('stop_primes', namespace='/test')
def socket_stop_primes(*args, **kwargs):
    global prime_pool, is_finding_primes

    if not is_finding_primes:
        emit('prime_status', {'status': 'not_running'})
        return

    is_finding_primes = False
    if prime_pool:
        prime_pool.terminate()
        prime_pool.join()

    emit('prime_status', {'status': 'stopped', 'count': len(primes_found)})


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True, allow_unsafe_werkzeug=True)
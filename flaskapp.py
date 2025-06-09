from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import itertools
from multiprocessing import Pool, cpu_count
from math import sqrt
from hwmon import HardwareMonitor
from utils import mylogger
# from waitress import serve
import time
import os

prime_pool = None
is_finding_primes = False
primes_found = []
connected_clients = 0
sensor_data = {}
is_monitoring = False
recording = False
recorded_measurements = []
recording_start_time = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

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
    cpus = processes or cpu_count()
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

#
# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/')
def primes_page():
    return render_template('primes.html')


@app.route('/api/start_primes', methods=['POST'])
def start_primes():
    global is_finding_primes

    if is_finding_primes:
        return jsonify({'status': 'calculating'})

    processes = request.json.get('processes') if request.json else None
    if processes:
        processes = max(1, int(processes))


    socketio.start_background_task(prime_finder_thread, processes)
    return jsonify({'status': 'running', 'processes': processes or cpu_count()})


@app.route('/api/stop_primes', methods=['POST'])
def stop_primes():
    primestop()

@socketio.on('connect', namespace='/test')
def handle_connect():
    global connected_clients
    connected_clients += 1
    logger.info(f"Client connected. Total clients: {connected_clients}")


@socketio.on('start_primes', namespace='/test')
def socket_start_primes(*args, **kwargs):
    global is_finding_primes

    if is_finding_primes:
        emit('prime_status', {'status': 'calculating'})
        return
    else:
        emit('prime_status', {'status': 'running'})

    # Get processes from arguments or use None to default to CPU count
    processes = None

    logger.info(args)
    if args and isinstance(args[0], dict) and 'processes' in args[0]:
        processes = max(1, int(args[0]['processes']))  # Ensure at least 1

    socketio.start_background_task(prime_finder_thread, processes)
    emit('prime_status', {'status': 'running', 'processes': processes or cpu_count()})


@socketio.on('disconnect', namespace='/test')
def handle_disconnect():
    global connected_clients, is_finding_primes, prime_pool

    connected_clients = max(0, connected_clients - 1)  # Ensure it doesn't go negative
    logger.info(f"Client disconnected. Remaining clients: {connected_clients}")

    # Stop prime finding if no clients are connected
    if connected_clients == 0 and is_finding_primes:
        logger.info("Stopping prime calculation - all clients disconnected")
        is_finding_primes = False
        if prime_pool:
            prime_pool.terminate()
            prime_pool.join()
            prime_pool = None

@socketio.on('stop_primes', namespace='/test')
def socket_stop_primes(*args, **kwargs):
    primestop()

@socketio.on('start_recording', namespace='/test')
def start_recording_handler(*args, **kwargs):
    global recording, recorded_measurements, recording_start_time
    if recording:
        emit('recording_status', {'status': 'calculating'})
        return
    recording = True
    recorded_measurements = []
    recording_start_time = time.time()
    emit('recording_status', {'status': 'recording_started'})

@socketio.on('save_recording', namespace='/test')
def save_recording_handler(*args, **kwargs):
    global recording, recorded_measurements, recording_start_time
    if not recorded_measurements:
        emit('recording_status', {'status': 'no_data_to_save'})
        return
    import datetime
    dt = datetime.datetime.fromtimestamp(recording_start_time)
    os.makedirs('recordings', exist_ok=True)
    filename = f"recordings/recording_{dt.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    import json
    with open(filename, 'w') as f:
        json.dump(recorded_measurements, f)
    recording = False
    emit('recording_status', {'status': 'saved', 'filename': filename})

@socketio.on('load_recording', namespace='/test')
def load_recording_handler(*args, **kwargs):
    import glob, json
    os.makedirs('recordings', exist_ok=True)
    files = sorted(glob.glob('recordings/recording_*.json'), reverse=True)
    if not files:
        emit('recording_status', {'status': 'no_recording_found'})
        return
    # Send the list of files to the client
    emit('recording_files', {'files': [os.path.basename(f) for f in files]})
    # If a specific file is requested, send its data
    if args and len(args) > 0 and isinstance(args[0], dict) and 'filename' in args[0]:
        filename = os.path.join('recordings', args[0]['filename'])
        if not os.path.exists(filename):
            emit('recording_status', {'status': 'file_not_found', 'filename': filename})
            return
        with open(filename, 'r') as f:
            data = json.load(f)
        emit('recording_status', {'status': 'loaded', 'filename': filename})
        emit('recording_data', {'data': data})

def primestop():
    global prime_pool, is_finding_primes

    if not is_finding_primes:
        emit('prime_status', {'status': 'waiting'})
        return

    is_finding_primes = False
    if prime_pool:
        prime_pool.terminate()
        prime_pool.join()

    emit('prime_status', {'status': 'stopped', 'count': len(primes_found)})


def hardware_monitor_thread():
    """Background task for monitoring hardware sensors"""
    global sensor_data, is_monitoring, recording, recorded_measurements
    if is_monitoring:
        return
    is_monitoring = True
    logger.info("Starting hardware monitoring")
    hw_monitor = HardwareMonitor("http://127.0.0.1:8086", logger=logger)
    logger.info("Hardware monitor initialized")
    try:
        while is_monitoring:
            # Update and get sensor data
            hw_monitor.update()
            logger.debug(hw_monitor.data)
            cpu_temp = 0
            if hw_monitor.data and hw_monitor.data.get("available"):
                sensor_data = hw_monitor.data["sensors"]

                # Log some key metrics
                cpu_temp = hw_monitor.get_cpu_temperature()
                cpu_load = hw_monitor.get_cpu_load()

                # Calculate active threads
                active_threads = 0
                if is_finding_primes and prime_pool:
                    active_threads = prime_pool._processes

                client_data = {
                    'cpu_temp': cpu_temp,
                    'cpu_load': cpu_load,
                    'active_threads': active_threads
                }

                # Record if recording is enabled
                if recording:
                    recorded_measurements.append({
                        'timestamp': time.time(),
                        **client_data
                    })

                # Send data via SocketIO to all connected clients
                socketio.emit('hardware_data', client_data, namespace='/test')
            else:
                logger.warning("Hardware monitoring service not available")

            # Emit to socket clients
            socketio.emit('sensor_update', sensor_data, namespace='/hwmon')
            if cpu_temp:
                logger.log(round(int(cpu_temp) - 40, -1), f"CPU temperature {cpu_temp}")
            # Sleep for some time before next update
            time.sleep(1)
    except Exception as e:
        logger.error(f"Hardware monitoring error: {e}")
    finally:
        is_monitoring = False
        logger.info("Hardware monitoring stopped")

# Add routes for controlling hardware monitoring
@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    global is_monitoring

    if is_monitoring:
        return jsonify({'status': 'calculating'})

    socketio.start_background_task(hardware_monitor_thread)
    return jsonify({'status': 'running'})


@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global is_monitoring

    if not is_monitoring:
        return jsonify({'status': 'waiting'})

    is_monitoring = False
    return jsonify({'status': 'stopping'})


# Add a route to get the latest sensor data
@app.route('/api/sensor_data')
def get_sensor_data():
    return jsonify(sensor_data)

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Flask app with hardware monitoring and prime finder.")
    parser.add_argument('--logfile', action='store_true', help="Enable logging to file.")
    parser.add_argument('--debug', action='store_true', help="Enable debug mode.")
    args = parser.parse_args()

    mainlogger = mylogger.init(args)
    logger = mainlogger.getChild('flaskapp')


    @app.before_request
    def start_monitoring_once():
        global is_monitoring
        if not is_monitoring:
            socketio.start_background_task(hardware_monitor_thread)


    # socketio.start_background_task(hardware_monitor_thread)
    # serve(app, host='0.0.0.0', port=80)
    socketio.run(app, host="0.0.0.0", port=80, debug=True, allow_unsafe_werkzeug=True)



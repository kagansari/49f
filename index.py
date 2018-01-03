# Kagan Sari
# 2011400207
import argparse
import simpy
import math
import random
import termcolor

# these variables can be modified with command line options
simulation_time = 1800  # how much time simulation will continue (sec)
simulation_count = 10  # how many simulation will it run
show_log = False  # whether logs should be printed
only_HU = False  # if set true, simulation will run as if no user but HU exists, used to calculate optimum throughput
only_sat = False  # if set true, simulation will run putting all HUs on sat, used to calculate minimum throughput
assign_random = False
no_queue = False

N_f_sat = 5  # Total number of satellite bands
N_f_ter = 10  # Total number of terrestrial bands

lambda_sat_PU = 0.15  # Arrival rate of PUs at satellite link (user/sec)
lambda_ter_PU = 0.8  # Arrival rate of PUs at terrestrial link (user/sec)
lambda_ter_SU = 0.5  # Arrival rate of SUs at terrestrial link (user/sec)
lambda_HU = 0.3  # Arrival rate of HUs at the system (user/sec)

W_sat = 36e6  # Bandwidth of satellite link (Hz)
W_ter = 2e6  # Bandwidth of terrestrial link (Hz)

f_sat = 20000e6  # Frequency of satellite link (Hz)
f_ter = 700e6  # Frequency of terrestrial link (Hz)

G_sat = 2.5e4  # Gain of the satellite
G_BS = 4e-5  # Gain of the base station
G_dev_HU = 6e-2  # Gain of a hybrid user
G_dev_PU_ter = 11e-2  # Gain of a primary user requesting service at terrestrial link
G_D_r = 6e-2  # Gain of a device

# R_BS = 300  # The radius of the BS (m)
d_sat = 300000  # Distance from satellite to earth (m)
d_BS = 150  # The distance between any user (PU,SU,HU) and the BS (m)

P_total_sat = 240  # Total transmission power of the satellite (W)
P_total_BS = 60  # Total transmission power of the BS (W)

P_ch_sat = P_total_sat / N_f_sat  # Per channel transmission power of the satellite (W)
P_ch_BS = P_total_BS / N_f_ter  # Per channel transmission power of the BS (W)

N_sat_0 = 1e-18  # Noise at satellite link (W/Hz)
N_ter_0 = 1.5e-19  # Noise at terrestrial link (W/Hz)

mean_base_content_size = 25e6  # Mean base content chunk size requested by an HU|PU|SU at satellite|terrestrial link (bit)
mean_enhancement_content_size = 5e6  # Mean enhancement content chunk size requested by an HU (bit)

c = 299792458  # speed of light (m/sec)

sum_content_size = 0  # total sum of fully transmitted base chunks and portion of succesfully transmitted enhancement chunks (bit)


class User(object):
    """priorities
    satellite: PUs|HUs fetching base chunk > HUs fetching enhancement chunk
    terrestrial: PUs fetching base chunk > HUs > SUs
    """
    priority = {
        'PU': {'base': {'sat': 1, 'ter': 1}},
        'SU': {'base': {'ter': 3}},
        'HU': {'base': {'sat': 1, 'ter': 2}, 'enhancement': {'sat': 2, 'ter': 2}}
    }
    """color printed on console
    yellow   : for HUs who have no network yet
    blue     : for PUs on terrestrial network
    purple   : for PUs and HUs on satellite network
    pale blue: for SUs and HUs on terrestrial network
    """
    color = {
        'PU': {'sat': 'magenta', 'ter': 'blue'},
        'SU': {'ter': 'cyan'},
        'HU': {None: 'yellow', 'sat': 'yellow', 'ter': 'yellow'}
    }

    def __init__(self, user_type, network_type, index):
        super(User, self).__init__()
        self.user_type = user_type  # PU|SU|HU
        self.network_type = network_type  # sat|ter|None (HUs have no network when initialized, algorithm decides which one)
        self.index = index  # order of the user, integer, starting with 1
        self.content = Content.get_random_content()
        self.chunk_type = None  # base|enhancement, chunk type this user is fetching or will fetch

    def __str__(self):
        if self.network_type:
            return self.user_type + '-' + self.network_type + '-' + str(self.index)
        else:
            return self.user_type + '-' + str(self.index)

    def get_received_power_strength(self):
        """calculate received power strenth by using space path loss model"""
        if self.user_type == 'PU' and self.network_type == 'sat':
            return (P_ch_sat * G_sat * G_D_r * c**2) / (4 * math.pi * f_sat * d_sat)**2
        elif self.user_type == 'PU' and self.network_type == 'ter':
            return (P_ch_BS * G_BS * G_dev_PU_ter * c**2) / (4 * math.pi * f_ter * d_BS)**2
        elif self.user_type == 'SU' and self.network_type == 'ter':
            return (P_ch_BS * G_BS * G_D_r * c**2) / (4 * math.pi * f_ter * d_BS)**2
        elif self.user_type == 'HU' and self.network_type == 'sat':
            return (P_ch_sat * G_sat * G_dev_HU * c**2) / (4 * math.pi * f_sat * d_sat)**2
        elif self.user_type == 'HU' and self.network_type == 'ter':
            return (P_ch_BS * G_BS * G_dev_HU * c**2) / (4 * math.pi * f_ter * d_BS)**2
        else:
            print('ERROR')

    def get_channel_capacity(self):
        """calculate corresponding channel capacity using with the Shannon’s capacity formula under Additive White Gaussian Noise"""
        # network type should be defined
        if not self.network_type:
            print('ERROR: network_type not assigned')

        power_strenth = self.get_received_power_strength()
        W = {'sat': W_sat, 'ter': W_ter}[self.network_type]  # choose bandwidth of the given network_type
        N = {'sat': N_sat_0, 'ter': N_ter_0}[self.network_type]  # choose noise of the given network_type
        channel_capacity = W * math.log(1 + (power_strenth / (N * W)), 2)  # Shannon’s capacity formula
        # print('channel capacity %s: %f Mhz' % (self, channel_capacity/1e6))
        return channel_capacity

    def get_service_duration(self):
        if not self.content:
            print('ERROR: content not assigned')

        if self.chunk_type == 'base':
            return self.content.base_size / self.get_channel_capacity()
        elif self.chunk_type == 'enhancement':
            return self.content.enhancement_size / self.get_channel_capacity()
        else:
            print('ERROR: invalid parameter')

    def get_priority(self):
        """priorities
        satellite: PUs|HUs fetching base chunk > HUs fetching enhancement chunk
        terrestrial: PUs fetching base chunk > HUs > SUs
        """
        return User.priority[self.user_type][self.chunk_type][self.network_type]

    def get_color(self):
        """color printed on console
        yellow   : for HUs who have no network yet
        blue     : for PUs on terrestrial network
        purple   : for PUs and HUs on satellite network
        pale blue: for SUs and HUs on terrestrial network
        """
        return User.color[self.user_type][self.network_type]

    def log(self, message, type=None):
        if not show_log:
            return
        color = self.get_color()
        termcolor.cprint('%f, %s: ' % (env.now, self), color, end='')
        termcolor.cprint(message, color)


class Content(object):
    """docstring for Content"""
    def __init__(self, base_size, enhancement_size, prob):
        super(Content, self).__init__()
        self.base_size = base_size
        self.enhancement_size = enhancement_size
        self.prob = prob

    @staticmethod
    def get_contents():
        """set up 100 contents"""
        contents = []
        prob = 0
        for i in range(0, 100):
            base_size = random.expovariate(1/mean_base_content_size)
            enhancement_size = random.expovariate(1/mean_enhancement_content_size)
            prob += 1/((i+1) * math.log(1.78*100))
            content = Content(base_size, enhancement_size, min(prob, 1))
            contents.append(content)
        return contents

    @staticmethod
    def get_random_content():
        """return a content according to zipf distribution"""
        rand = random.random()
        for content in contents:
            if rand <= content.prob:
                return content


class Network(object):
    def __init__(self, network_type, capacity):
        super(Network, self).__init__()
        self.network_type = network_type  # sat|ter
        self.resource = simpy.PreemptiveResource(env, capacity=capacity)  # resource object with given capacity

    def serve(self, user, preempt):
        """make a user use this network"""
        left_time = user.get_service_duration()
        while left_time:
            request = self.resource.request(priority=user.get_priority(), preempt=preempt)
            request.user = user
            user.log('requested %s, gonna use for %f' % (self.network_type, left_time))
            yield request
            try:
                start_time = env.now
                user.log('started using %s, will release in %f' % (self.network_type, left_time))
                yield env.timeout(left_time)
                left_time = 0
            except simpy.Interrupt as interrupt:
                left_time -= env.now - start_time
                user.log('interrupted from %s, %f left' % (self.network_type, left_time))
            finally:
                self.resource.release(request)

    def is_full(self):
        """true if all slots in resource of this network are being used"""
        return self.resource.count == self.resource.capacity

    def get_request(self, user_type):
        """return a user with user_type using this resource, return None if there is not any"""
        for req in self.resource.users:
            if req.user.user_type == user_type:
                return req


def init_arguments():
    """initialize command line arguments"""
    global simulation_time, simulation_count, show_log, only_HU, only_sat, assign_random, no_queue
    parser = argparse.ArgumentParser(description='Run simulation for SIMULATION_TIME seconds for SIMULATION_COUNT times')
    parser.add_argument('--sim-time', help='simulation time in secs', dest='simulation_time', type=int, default=simulation_time)
    parser.add_argument('--sim-count', help='how many time simulation runs', dest='simulation_count', type=int, default=simulation_count)
    parser.add_argument('--log', help='show every step of simulation', action='store_true', dest='show_log', default=show_log)
    parser.add_argument('--optimum', help='run simulation for only HUs', action='store_true', dest='only_HU', default=only_HU)
    parser.add_argument('--minimum', help='put HUs on only satellite network', action='store_true', dest='only_sat', default=only_sat)
    parser.add_argument('--random', help='put HUs randomly', action='store_true', dest='assign_random', default=assign_random)
    parser.add_argument('--no-queue', help='queue is disabled', action='store_true', dest='no_queue', default=no_queue)
    args = parser.parse_args()
    simulation_time = args.simulation_time
    simulation_count = args.simulation_count
    show_log = args.show_log
    only_HU = args.only_HU
    only_sat = args.only_sat
    assign_random = args.assign_random
    no_queue = args.no_queue


def assign_network(user):
    """assign a network to user"""
    req_to_drop = None  # request to be dropped
    # if user is PU on satellite then drop any HU fetching enhancement chunk
    if user.user_type == 'PU' and user.network_type == 'sat':
        if sat_net.is_full():
            user.log('sat network is full')
            req_to_drop = sat_net.get_request('HU')
            if req_to_drop:
                user.log('is dropping a %s' % req_to_drop.user.user_type)
            else:
                user.log('there is no HU to drop in the network')

    # if user is PU on terrestrial then drop any SUs, if there is no SU then drop HUs fetching enhancement chunks
    if user.user_type == 'PU' and user.network_type == 'ter':
        if ter_net.is_full():
            user.log('ter network is full')
            # for each one using resource find an SU, if there is no SU then find an HU
            req_to_drop = ter_net.get_request('SU')
            if not req_to_drop:
                req_to_drop = ter_net.get_request('HU')
            if req_to_drop:
                user.log('is dropping a %s' % req_to_drop.user.user_type)
            else:
                user.log('there is no SU or HU to drop in the network')

    # if user is HU then decide which network she will use
    if user.user_type == 'HU':
        if ter_net.is_full() and sat_net.is_full():
            user.network_type = 'ter'
        elif ter_net.is_full():
            user.network_type = 'sat'
        else:
            user.network_type = 'ter'

        if only_sat:
            user.network_type = 'sat'

        if assign_random:
            rand = random.random()
            if rand < .5:
                user.network_type = 'ter'
            else:
                user.network_type = 'sat'

    return req_to_drop


def request_resource(user):
    """make user fetch content using satellite or terrestrial resource, or make it wait in queue"""
    global sum_content_size

    preempt = assign_network(user)
    network = {'sat': sat_net, 'ter': ter_net}[user.network_type]  # choose network type of incoming user
    user.chunk_type = 'base'

    if no_queue and network.is_full():
        return

    yield from network.serve(user, preempt)

    user.log('got her base chunk')
    if user.user_type == 'HU':
        sum_content_size += user.content.base_size

    if user.user_type == 'HU':  # make HUs get enhancement chunk
        user.chunk_type = 'enhancement'
        if no_queue and network.is_full():
            return
        yield from network.serve(user, preempt)
        user.log('got her enhancement chunks')
        sum_content_size += user.content.enhancement_size


def arrival_process(arrival_rate, user_type, network_type=None):
    """poison process generator according to parameters
    arrival_rate: lambda for exponential distribution
    user_type   : PU|SU|HU
    network_type: sat|ter
    """
    i = 0
    while True:
        i += 1
        interval = random.expovariate(arrival_rate)
        # if option is set then no PU or SU arrives
        if user_type != 'HU' and only_HU:
            interval = simulation_time
        yield env.timeout(interval)  # wait for given time...
        user = User(user_type, network_type, i)  # ...and create new user
        user.log('arrived')
        env.process(request_resource(user))


init_arguments()
print('Running simulation %d times with durations of %d secs' % (simulation_count, simulation_time))
throughput_sum = 0
print('Throughputs:', end=' ')
for i in range(0, simulation_count):
    sum_content_size = 0
    # set up contents list 100
    contents = Content.get_contents()
    # set up simulation environment
    env = simpy.Environment()
    # networks
    sat_net = Network('sat', N_f_sat)
    ter_net = Network('ter', N_f_ter)
    # arrival processes
    PU_sat_arrival_proc = env.process(arrival_process(lambda_sat_PU, 'PU', 'sat'))
    PU_ter_arrival_proc = env.process(arrival_process(lambda_ter_PU, 'PU', 'ter'))
    SU_ter_arrival_proc = env.process(arrival_process(lambda_ter_SU, 'SU', 'ter'))
    HU_arrival_proc = env.process(arrival_process(lambda_HU, 'HU'))
    env.run(until=simulation_time)
    throughput = (sum_content_size / simulation_time) * 1e-6
    throughput_sum += throughput
    print('%f' % throughput, end=', ')
print('\nAverage throughput: %f Mbit' % (throughput_sum / simulation_count))

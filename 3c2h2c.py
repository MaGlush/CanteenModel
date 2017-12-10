import simpy
import random
from enum import Enum

# перечисление, описывающее все возможные варианты маршрутов
class Way(Enum):
    long_way = 'по маршруту горячие блюда -> напитки -> касса'
    middle_way = 'по маршруту холодные закуски -> напитки -> касса'
    short_way = 'по маршруту напитки -> касса'

# счетчик для подсчета студентов
counter = 0
# создание среды моделирования
env = simpy.Environment()
# ресурсы пунктов выдачи
services = {Way.long_way: simpy.Resource(env), 
    Way.middle_way: simpy.Resource(env), 
    Way.short_way: simpy.Resource(env)}
# ресуры касс
cashiers = [simpy.Resource(env), simpy.Resource(env), simpy.Resource(env)]
# списки для подсчета средних и максимальных задержек и длинн очередей для кажого случая
services_queue_length = {Way.long_way: [], 
    Way.middle_way: [], 
    Way.short_way: []}
services_queue_time = {Way.long_way: [], 
    Way.middle_way: [], 
    Way.short_way: []}
cashiers_queue_length = [[], [], []]
cashiers_queue_time = {Way.long_way: [[], [], []], 
    Way.middle_way: [[], [], []], 
    Way.short_way: [[], [], []]}
all_queue_time = {Way.long_way: [], 
    Way.middle_way: [], 
    Way.short_way: []}
all_clients = []


class Student:
    # инициализатор класса клиента
    def __init__(self, way):
        # запоминаем номер клиента для последующего логирования
        global counter
        counter += 1
        self.counter = counter
        # запоминаем маршрут клиента
        self.way = way
        # в инициализаторе сразу определям сколько клиент проведет 
        # на выдаче и на кассе продвигаясь по выбранному маршруту
        if way == Way.long_way:  # по маршруту горячие блюда -> напитки -> касса
            self.service_time = random.randrange(25, 60) + random.randrange(5, 20)
            self.cashier_time = random.randrange(20, 40) + random.randrange(5, 10)
        elif way == Way.middle_way:  # по маршруту холодные закуски -> напитки -> касса
            self.service_time = random.randrange(30, 90) + random.randrange(5, 20)
            self.cashier_time = random.randrange(5, 15) + random.randrange(5, 10)
        elif way == Way.short_way:  # по маршруту напитки -> касса
            self.service_time = random.randrange(5, 20)
            self.cashier_time = random.randrange(5, 10)

    # занимаем очередь по выбранному маршруту и ожидаем в ней
    def wait_service(self):
        with services[self.way].request() as req:
            services_queue_length[self.way] +=\
                [1 if not len(services_queue_length[self.way]) else services_queue_length[self.way][-1]+1]
            time = env.now
            print('{0}: wait for {1} service-queue student {2}'
                .format(env.now, self.way, self.counter))
            yield req
            yield env.timeout(self.service_time)
            services_queue_length[self.way] +=\
                [services_queue_length[self.way][-1]-1]
            services_queue_time[self.way] += [env.now - time]
            print('{0}: service free student {1} after {2}'
                .format(env.now, self.counter, self.service_time))

    # занимаем очередь к наиболее пустой очереди к кассе и ожидаем в ней
    def wait_cashier(self):
        if len(cashiers_queue_length[0]) >= len(cashiers_queue_length[1]):
            queue_num = 1 if len(cashiers_queue_length[2]) >= len(cashiers_queue_length[1]) else 2
        else:
            queue_num = 0 if len(cashiers_queue_length[2]) >= len(cashiers_queue_length[0]) else 2
        with cashiers[queue_num].request() as req:
            cashiers_queue_length[queue_num]+=\
                [1 if not len(cashiers_queue_length[queue_num]) else cashiers_queue_length[queue_num][-1]+1]
            time = env.now
            print('{0}: wait for cashier-queue student {1}'.format(env.now, self.counter))
            yield req
            yield env.timeout(self.cashier_time)
            cashiers_queue_length[queue_num] += [cashiers_queue_length[queue_num][-1]-1]
            cashiers_queue_time[self.way][queue_num] += [env.now - time]
            print('{0}: cashier free student {1} after {2}'
                .format(env.now, self.counter, self.cashier_time))

    # полная обработка одного клиента
    def processes(self):
        global all_clients
        all_clients += [1 if not len(all_clients) else all_clients[-1]+1]
        time = env.now
        yield env.process(self.wait_service())
        yield env.process(self.wait_cashier())
        all_queue_time[self.way] += [env.now - time]
        all_clients += [all_clients[-1]-1]

queue = []

def man(env, service, cashier):
    while True:
        global queue, all_clients
        # интервал прибытия между группами
        yield env.timeout(random.expovariate(1/30))
        #  моделирование потока по группам
        p = random.random()
        if p <= 0.5: #  1 человек
            students_num = 1
        elif p <= 0.8: #  2 человека
            students_num = 2
        elif p <= 0.9: #  3 человека
            students_num = 3
        else:
            students_num = 4
        print('{0}: New group with {1} student'.format(env.now, students_num))
        # распределение по маршрутам
        for i in range(students_num):
            p = random.random()
            if p <= 0.8: #  Way.long_way
                student = Student(Way.long_way)
            elif p <= 0.95: #  Way.middle_way
                student = Student(Way.middle_way)
            else:  # Way.short_way
                student = Student(Way.short_way)
            env.process(student.processes())

random.seed()
env.process(man(env, services, cashiers))
env.run(until=90*60)  # 90 минут работы системы

from numpy import average, max

print('Максимальное и среднее число клиентов к пунктам выдачи')
for i, j in services_queue_length.items():
    print('Max ', i.value, max(j))
    print('Avg ', i.value, average(j))
print('Максимальное и среднее число клиентов к кассам')
for i in cashiers_queue_length:
    print('Max ', max(i))
    print('Avg ', average(i))
print('Средняя и максимальная задержка в очередях по каждому маршруту')
for i, j in services_queue_time.items():
    print('Avg ', i.value, average(j))
    print('Max ', i.value, max(j))
print('Средняя и максимальная задержка в очередях к кассам для всех типов клиентов')
for i, j in cashiers_queue_time.items():
    for k in range(len(j)):
        print('Avg для клиента ', i.value, 'касса: ', k+1, average(j[k]))
        print('Max для клиента ', i.value, 'касса: ', k+1, max(j[k]))
print('Средняя и максимальная задержка в очередях для всех типов клиентов')
for i, j in all_queue_time.items():
    print('Avg для клиента ', i.value, average(j))
    print('Max для клиента ', i.value, max(j))

print('Среднее и максимальное число клиентов во всей системе')
print('Avg ', average(all_clients))
print('Max ', max(all_clients))
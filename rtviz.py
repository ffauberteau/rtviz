#!/usr/bin/env python3
#
# Copyright (c) 2016, Frédéric Fauberteau
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY FRÉDÉRIC FAUBERTEAU AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import json
import sys

ARROW_HEIGHT = 0.75
JOB_HEIGHT   = 0.5 # height of the job rectangle
PROC_VSPACE  = 0.5 # space between two consecutive proc timeline
TASK_HEIGHT  = 1   # height of a task (activation arrow)
TIME_UNIT    = 1 # lenght of a time unit

class Job:
    def __init__(self, schedule, release, executions, deadline, task):
        self._schedule = schedule
        self._release  = release
        self._executions = executions
        self._deadline = deadline
        self._task = Task(task, schedule)
        self._processors = [Processor(e['processor'], schedule) for e in self._executions]
        if self._task not in schedule:
            schedule += self._task
        for proc in self._processors:
            if proc not in schedule:
                schedule += proc

    def get_deadline(self):
        return self._deadline

    def get_finish(self):
        finish = 0
        for execution in self.executions:
           exec_finish = execution['start'] + execution['time'] 
           if exec_finish > finish:
               finish = exec_finish
        return finish

    def get_executions(self):
        return self._executions

    def get_first_execution(self):
        first_execution = None
        for execution in self.get_executions():
            if first_execution is None or execution['start'] < first_execution['start']:
                first_execution = execution
        return first_execution

    def get_last_execution(self):
        last_execution = None
        for execution in self.get_executions():
            if last_execution is None or execution['start'] > first_execution['start']:
                last_execution = execution
        return last_execution

    def get_start(self):
        start = None
        for execution in self.executions:
            exec_start = execution['start']
            if start is None or exec_start < start:
                start = exec_start
        return exec_start

    def get_release(self):
        return self._release

    def get_task(self):
        return self._task

    def get_x_deadline(self):
        return (self.get_deadline() - self._schedule.get_start()) * TIME_UNIT

    def get_y_deadline(self):
        proc = self._schedule.processors[self.get_last_execution()['processor']]
        return self.get_task().get_y(proc)

    def get_x_release(self):
        return (self.get_release() - self._schedule.get_start()) * TIME_UNIT

    def get_y_release(self):
        proc = self._schedule.processors[self.get_first_execution()['processor']]
        return self.get_task().get_y(proc)

    def get_x(self, execution):
        return (execution['start'] - self._schedule.get_start()) * TIME_UNIT

    def get_y(self, execution):
        proc = self._schedule.processors[execution['processor']]
        return self.get_task().get_y(proc)

    def get_width(self, execution):
        return execution['time'] * TIME_UNIT

class Task:
    def __init__(self, ident, schedule):
        self._ident = ident
        self._schedule = schedule

    def get_id(self):
        return self._ident

    def get_x(self, processor):
        return processor.get_x()

    def get_y(self, processor):
        return processor.get_y() + (self._schedule.get_ntask() - self.get_id()) * TASK_HEIGHT

    def get_width(self):
        return (self._schedule.get_duration() + 1) * TIME_UNIT

    def __eq__(self, other):
        if self.get_id() is other.get_id():
            return True
        return False

class Processor:
    def __init__(self, ident, schedule):
        self._ident = ident
        self._schedule = schedule

    def get_id(self):
        return self._ident

    def get_height(self):
        return TASK_HEIGHT * self._schedule.get_ntask() + PROC_VSPACE

    def get_x(self):
        return 0

    def get_y(self):
        return (self._schedule.get_nprocessor() - self.get_id()) * self.get_height()

    def __eq__(self, other):
        if self.get_id() is other.get_id():
            return True
        return False

    def __str__(self):
        return 'P' + str(self.get_id())

class ScheduleDrawer:
    def __init__(self, schedule):
        self._schedule = schedule

    def get_job(self, job):
        rx = job.get_x_release()
        ry = job.get_y_release()
        dx = job.get_x_deadline()
        dy = job.get_y_deadline()
        s = ''
        for execution in job.get_executions():
            x = job.get_x(execution)
            y = job.get_y(execution)
            w = job.get_width(execution)
            h = JOB_HEIGHT
            s += '  \\draw'
            try:
                color = execution['color']
                s += '[fill=' + color + ', fill opacity=0.5]'
            except KeyError:
                pass
            s += ' (' + str(x) + ',' + str(y) + ') rectangle (' + str(x + w) + ',' + str(y + h) + ');\n'
        s += '  \\draw[->] (' + str(rx) + ',' + str(ry) + ') -- (' + str(rx) + ',' + str(ry + ARROW_HEIGHT) + ');\n'
        s += '  \\draw[<-] (' + str(dx) + ',' + str(dy) + ') -- (' + str(dx) + ',' + str(dy + ARROW_HEIGHT) + ');'
        return s

    def get_timeline(self, task, processor):
        x = task.get_x(processor)
        y = task.get_y(processor)
        w = task.get_width()
        h = y
        d = self._schedule.get_duration() + 1
        n = self._schedule.get_ntask()
        o = self._schedule.get_start()
        s = '  % task ' + str(task.get_id()) + ' on processor ' + str(processor.get_id()) + '\n' + \
                '  \\node at (' + str(x - TIME_UNIT / 2) + ',' + str(y + TASK_HEIGHT / 2) + ') {$\\tau_' + str(task.get_id()) + '$};\n' + \
                '  \\draw[->] ' + \
                '(' + str(x - 1) + ',' + str(y) + ')' + \
                ' -- ' + \
                '(' + str(w) + ',' + str(h) + ');\n' + \
                '  \\foreach \\x in {' + ','.join([str(n) for n in range(0, d, TIME_UNIT)]) + '}{\n' + \
                '    \\draw (\\x,' + str(y + 0.05) + ') -- (\\x,' + str(y - 0.05) + ');\n' + \
                '  }\n'
        for r in range(0, d, TIME_UNIT * 5):
            s += '  \\draw (' + str(r) + ',' + str(y + 0.1) + ') -- (' + str(r) + ',' + str(y - 0.1) + ');\n'
            if task.get_id() is n:
                s += '  \\node at (' + str(r) + ',' + str(y - 0.3) + ') {' + str(r + o) + '};\n'

        return s

    def get_timelines(self, processor):
        return '\n'.join([self.get_timeline(t, processor) for t in self._schedule.tasks.values()])

    def __str__(self):
        s = '\\begin{tikzpicture}\n' + \
            '\n'.join([self.get_timelines(p) for p in self._schedule.processors.values()]) + '\n' + \
            '\n'.join([self.get_job(j) for j in self._schedule.jobs]) + '\n' + \
            '\\end{tikzpicture}'
        return s

class Schedule:
    def __init__(self):
        self.jobs = []
        self.tasks = {}
        self.processors = {}

    def get_start(self):
        start = None
        for job in self.jobs:
            release = job.get_release()
            if start is None or release < start:
                start = release
        return start

    def get_finish(self):
        finish = 0
        for job in self.jobs:
            deadline = job.get_deadline()
            if deadline > finish:
                finish = deadline
        return finish

    def get_duration(self):
        return self.get_finish() - self.get_start()

    def get_nprocessor(self):
        return len(self.processors)

    def get_ntask(self):
        return len(self.tasks)

    def processor_x(self, processor_id):
        return 0

    def processor_y(self, processor_id):
        return (TASK_HEIGHT * self.ntask() + PROC_VSPACE) * (self.nprocessor() - processor_id)

    def __contains__(self, item):
        if type(item) is Task:
            return item in self.tasks.values()
        if type(item) is Processor:
            return item in self.processors.values()
        return False

    def __iadd__(self, other):
        if type(other) is Job:
            self.jobs.append(other)
        if type(other) is Task:
            self.tasks[other.get_id()] = other
        if type(other) is Processor:
            self.processors[other.get_id()] = other
        return self

    def __str__(self):
        drawer = ScheduleDrawer(self)
        return str(drawer)

def parse(filename):
    sched = Schedule()

    trace = json.load(filename)
    for job_param in trace['job']:
        job = Job(sched, **job_param)
        sched += job
    return sched

def main():
    parser = argparse.ArgumentParser(
            description='Real-time scheduling vizualiser'
            )
    parser.add_argument('files', metavar='FILE', type=open, nargs='+',
            help='file to parse'
            )
    parser.add_argument('-o', '--output', type=argparse.FileType('w'),
            default=sys.stdout, help='output file [defaul=stdout]'
            )
    args = parser.parse_args()
    for f in args.files:
        try:
            sched = parse(f)
            print(sched, file=args.output)
        finally:
            f.close()

if __name__ == '__main__':
    sys.exit(main())

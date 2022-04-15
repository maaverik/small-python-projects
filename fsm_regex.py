
def prepare_coroutine(fn):
    """
    To be used as a decorator for priming coroutines.
    The state methods this fn wraps are only called once, 
    so the priming logic does not run more than once
    """
    def wrapper(*args, **kwargs):
        cr = fn(*args, **kwargs)
        cr.send(None)   # to prime the coroutine and get it to the yield statement
        return cr
    return wrapper


class FSM:
    """
    This class is used to model a finite state machine for matching the regular expression `ab*c`.
    It has four states - start, s1, s2 and s3 (final).
    """

    def __init__(self):
        self.start = self.create_start()
        self.s1 = self.create_s1()
        self.s2 = self.create_s2()
        self.s3 = self.create_s3()

        self.current_state = self.start
        self.failed = False     # received input for which transition is undefined

    def send(self, char: str):
        """
        Sends given input to current state for transition; if a StopIteration exception is returned,
        it captures it and marks the failed flag.
        """
        try:
            self.current_state.send(char)
        except StopIteration:
            self.failed = True

    def found_match(self):
        """
        Returns whether the input so far matches the given regex
        """
        return (not self.failed) and (self.current_state == self.s3)

    @prepare_coroutine
    def create_start(self):
        while True:
            char = yield
            if char == 'a':
                self.current_state = self.s1
            else:
                break

    @prepare_coroutine
    def create_s1(self):
        while True:
            char = yield
            if char == 'b':
                self.current_state = self.s2
            elif char == 'c':
                self.current_state = self.s3
            else:
                break

    @prepare_coroutine
    def create_s2(self):
        while True:
            char = yield
            if char == 'b':
                self.current_state = self.s2
            elif char == 'c':
                self.current_state = self.s3
            else:
                break

    @prepare_coroutine
    def create_s3(self):
        while True:
            char = yield
            break   # this is the final state


def does_match(text: str):
    evaluator = FSM()
    for char in text:
        evaluator.send(char)
    return evaluator.found_match()


if __name__ == '__main__':
    print(does_match('ac'))
    print(does_match('abc'))
    print(does_match('abbbc'))
    print(does_match('abd'))
    print(does_match('c'))

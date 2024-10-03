try:
    from multiprocessing import shared_memory
except ImportError:
    shared_memory = None


class Page:
    '''
    Memory page.
    '''

    def __init__(self, view, offset):
        self.view = view
        self.offset = offset
        self.is_free = True

    def use(self):
        self.is_free = False

    def free(self):
        self.is_free = True

    def close(self):
        self.view.release()


class Buffer:
    '''
    Manage the buffer memory to receive raw netlink data.
    '''

    def __init__(self, mode='internal', size=10485760, page_size=32768):
        self.mode = mode
        self.size = size
        self.page_size = page_size
        if self.mode == 'internal':
            self.mem = None
            self.buf = bytearray(self.size)
        elif self.mode == 'shared':
            if shared_memory is None:
                raise ModuleNotFoundError('shared memory buffer not supported')
            self.mem = shared_memory.SharedMemory(create=True, size=self.size)
            self.buf = self.mem.buf
        self.view = memoryview(self.buf)
        self.directory = {}
        for index in range(size // page_size):
            offset = index * page_size
            self.directory[index] = Page(
                self.view[offset : offset + self.page_size], offset
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_free_page(self):
        for index, page in self.directory.items():
            if page.is_free:
                page.use()
                return page
        raise MemoryError('no free memory pages available')

    def close(self):
        for page in self.directory.values():
            page.close()
        self.view.release()
        if self.mode == 'shared':
            self.mem.close()
            self.mem.unlink()

    def __getitem__(self, key):
        return self.directory[key]

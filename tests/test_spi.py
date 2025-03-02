import spidev
import threading
from queue import Queue


class SPIHandler:
    def __init__(self, bus=0, device=0, max_speed=10_000_000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = max_speed
        self.spi.mode = 0  # Ensure correct SPI mode

        self.spi_queue = Queue()  # Task queue for SPI transactions
        self.spi_lock = threading.Lock()  # Ensure only one SPI transfer at a time

        self.spi_worker_thread = threading.Thread(target=self.spi_worker, daemon=True)
        self.spi_worker_thread.start()

    def spi_worker(self):
        """Thread worker to process SPI tasks from the queue."""
        while True:
            task = self.spi_queue.get()
            if task is None:  # Stop condition
                break
            with self.spi_lock:
                if task["type"] == "write":
                    self.spi.xfer2(task["data"])
                elif task["type"] == "read":
                    task["result"].append(
                        self.spi.xfer2(task["data"])
                    )  # Store the result
            self.spi_queue.task_done()

    def write(self, data):
        """Queues a write operation."""
        self.spi_queue.put({"type": "write", "data": data})

    def read(self, data):
        """Queues a read operation and returns the result."""
        result = []
        self.spi_queue.put({"type": "read", "data": data, "result": result})
        self.spi_queue.join()  # Wait for task completion
        return result[0] if result else None  # Return received SPI data

    def close(self):
        """Clean up SPI resources."""
        self.spi_queue.put(None)  # Stop worker thread
        self.spi_worker_thread.join()
        self.spi.close()

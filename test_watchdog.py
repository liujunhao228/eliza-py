#!/usr/bin/env python3
"""测试 watchdog 文件监控"""

import time
import threading
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TestHandler(FileSystemEventHandler):
    def __init__(self):
        self.events = []
    
    def on_modified(self, event):
        if event.is_directory:
            return
        print(f"[事件] 文件修改：{event.src_path}")
        self.events.append(('modified', event.src_path, time.time()))
    
    def on_moved(self, event):
        if event.is_directory:
            return
        print(f"[事件] 文件移动：{event.dest_path}")
        self.events.append(('moved', event.dest_path, time.time()))

def test_watchdog():
    script_path = Path(r"F:\eliza-py\alice\scripts\demo.yaml")
    watch_dir = script_path.parent
    
    print(f"监控目录：{watch_dir}")
    print(f"监控文件：{script_path}")
    print(f"文件存在：{script_path.exists()}")
    
    handler = TestHandler()
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()
    
    print("\n✅ 监控已启动，请在 30 秒内修改 demo.yaml 文件...")
    print("   修改后等待 2 秒查看事件\n")
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
    
    print(f"\n捕获到的事件：{len(handler.events)}")
    for event in handler.events:
        print(f"  - {event}")

if __name__ == "__main__":
    test_watchdog()

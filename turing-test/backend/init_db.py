#!/usr/bin/env python3
"""
数据库初始化脚本
生成邀请码并创建数据库表
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from auth import create_invite_codes, get_invite_code_stats
from models import InviteCode

def init_database():
    """创建数据库表"""
    print("📦 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")

def generate_invite_codes(count=100, length=6):
    """生成邀请码"""
    print(f"🔑 生成 {count} 个邀请码...")
    
    db = SessionLocal()
    try:
        codes = create_invite_codes(db, count, length)
        
        # 保存到文件
        with open('invite_codes.txt', 'w', encoding='utf-8') as f:
            f.write("# 图灵测试邀请码\n")
            f.write(f"# 共 {len(codes)} 个\n\n")
            for code in codes:
                f.write(code + '\n')
        
        print(f"✅ 已生成 {len(codes)} 个邀请码")
        print("📄 邀请码已保存到 invite_codes.txt")
        
        # 显示前 10 个作为示例
        print("\n前 10 个邀请码示例:")
        for code in codes[:10]:
            print(f"  {code}")
        if len(codes) > 10:
            print(f"  ... 还有 {len(codes) - 10} 个")
            
    finally:
        db.close()

def show_stats():
    """显示统计信息"""
    db = SessionLocal()
    try:
        stats = get_invite_code_stats(db)
        print("\n📊 邀请码统计:")
        print(f"  总数：{stats['total']}")
        print(f"  已使用：{stats['used']}")
        print(f"  剩余：{stats['remaining']}")
    finally:
        db.close()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            show_stats()
            return
        elif sys.argv[1] == '--count' and len(sys.argv) > 2:
            count = int(sys.argv[2])
            init_database()
            generate_invite_codes(count)
            return
    
    # 默认操作
    print("🧪 图灵测试社交实验平台 - 数据库初始化")
    print("=" * 50)
    
    init_database()
    generate_invite_codes()
    show_stats()
    
    print("\n" + "=" * 50)
    print("✅ 初始化完成！")
    print("\n下一步:")
    print("1. 查看 invite_codes.txt 获取邀请码")
    print("2. 运行：python main.py 启动服务器")
    print("3. 访问：http://localhost:8000")

if __name__ == '__main__':
    main()

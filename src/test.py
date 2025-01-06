from base import Base

class Test(Base):
    '''テスト用の処理'''
    def __init__(self):
        super().__init__(use_db = False, use_api = False)

    def main(self):
        '''テスト処理'''
        result = self.service.board_mold.main()
        if result == False:
            return

if __name__ == '__main__':
    test = Test()
    test.main()
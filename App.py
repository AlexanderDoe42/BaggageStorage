from transitions import Machine
from transitions.extensions.states import add_state_features
from transitions.extensions.asyncio import AsyncTimeout, AsyncMachine
import asyncio
from websockets.server import serve
import json


CONST_PASSWORD = '1234'
CONST_MAX_TIME_DOOR_OPENED = 7
CONST_WRONG_PASSWORD_STATE_TIME = 3
CONST_HOST = 'localhost'
CONST_PORT = 47782


@add_state_features(AsyncTimeout)
class CustomStateMachine(AsyncMachine):
    pass


class BaggageStorage(object):

    states = [
        {'name': 'enter password', },
        {'name': 'wrong password', 'timeout': CONST_WRONG_PASSWORD_STATE_TIME, 'on_timeout': 'timeout_on_wrong_password'},
        {'name': 'door opened', 'timeout': CONST_MAX_TIME_DOOR_OPENED, 'on_timeout': 'opened_too_long'},
        {'name': 'close the door', }
    ]

    transitions = [
        { 'trigger': 'provide_password', 'source': 'enter password', 'dest': 'wrong password', 'unless': 'isCorrectPassword'},
        { 'trigger': 'provide_password', 'source': 'enter password', 'dest': 'door opened', 'conditions': 'isCorrectPassword'},
        { 'trigger': 'timeout_on_wrong_password', 'source': 'wrong password', 'dest': 'enter password'},
        { 'trigger': 'opened_too_long', 'source': 'door opened', 'dest': 'close the door'},
        { 'trigger': 'close_button_pressed', 'source': 'door opened', 'dest': 'enter password'},
        { 'trigger': 'close_button_pressed', 'source': 'close the door', 'dest': 'enter password'}
    ]

    def __init__(self, password, onStateChangeEvent):

        self.onStateChangeEvent = onStateChangeEvent
        self.password = password
        self.machine = CustomStateMachine(
            model=self,
            states=BaggageStorage.states,
            transitions=BaggageStorage.transitions,
            initial='enter password',
            after_state_change='notifyClient'
        )

    def isCorrectPassword(self, password = ''):
        return password == CONST_PASSWORD
    
    def notifyClient(self, e = ''):
        self.onStateChangeEvent.set()


if __name__ == '__main__':

    async def echo(websocket):
        onStateChangeEvent = asyncio.Event()
        baggageStorage = BaggageStorage(CONST_PASSWORD, onStateChangeEvent)
        await asyncio.sleep(0.1)
        await websocket.send(baggageStorage.state)

        async def onStateChangeWaiter(onStateChangeEvent):
            while True:
                await onStateChangeEvent.wait()
                await websocket.send(baggageStorage.state)
                onStateChangeEvent.clear()

        asyncio.create_task(onStateChangeWaiter(onStateChangeEvent))

        async for message in websocket:
            event = json.loads(message)
            print('from client message')
            
            match event['type']:
                case 'provide_password':
                    await baggageStorage.provide_password(event['value'])
                case 'close':
                    await baggageStorage.close_button_pressed()
                case _:
                    print('error')

    async def main():
        async with serve(echo, CONST_HOST, CONST_PORT):
            await asyncio.Future()

    asyncio.run(main())

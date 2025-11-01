from app.ingternal.modules.classes.baseModules import BaseModule
from app.ingternal.modules.arrays.serviceDataPoll import servicesDataPoll, ObservableDict
from app.configuration.settings import SERVICE_POLL, SERVICE_DATA_POLL
from .services.MqttService import MqttService
from .settings import MQTT_SERVICE_PATH, MQTT_PASSWORD, MQTT_BROKER_IP, MQTT_PORT, MQTT_USERNAME, MQTT_MESSAGES
from app.pkg import itemConfig, ConfigItemType, __config__
from .device_field_set import device_set_value
import asyncio
from typing import Optional

class Module(BaseModule):
    
    @classmethod
    async def start(cls):
        await super().start()

        services: ObservableDict = servicesDataPoll.get(SERVICE_POLL)
        service_dara: ObservableDict = servicesDataPoll.get(SERVICE_DATA_POLL)
        mqtt_service: Optional[MqttService] = services.get(MQTT_SERVICE_PATH)
        service_dara.set(MQTT_MESSAGES, {})

        restart_task: asyncio.Task | None = None
        debounce_delay = 0.5  # время ожидания после последнего изменения

        async def schedule_restart(*_):
            """Асинхронно откладывает рестарт mqtt_service"""
            global restart_task

            # если уже запланирован — отменяем старый
            if restart_task and not restart_task.done():
                restart_task.cancel()

            async def delayed_restart():
                try:
                    await asyncio.sleep(debounce_delay)
                    await mqtt_service.restart()
                except asyncio.CancelledError:
                    pass  # нормально, просто отменили предыдущий таймер

            # создаём новую задачу
            restart_task = asyncio.create_task(delayed_restart())

        print(mqtt_service)

        __config__.register_config(
            itemConfig(tag="mqtt", key=MQTT_USERNAME, type=ConfigItemType.TEXT, value="root"),
            schedule_restart
        )

        __config__.register_config(
            itemConfig(tag="mqtt", key=MQTT_PASSWORD, type=ConfigItemType.PASSWORD, value="root"),
            schedule_restart
        )

        __config__.register_config(
            itemConfig(tag="mqtt", key=MQTT_BROKER_IP, type=ConfigItemType.TEXT, value="mosquitto"),
            schedule_restart
        )

        __config__.register_config(
            itemConfig(tag="mqtt", key=MQTT_PORT, type=ConfigItemType.NUMBER, value="1883"),
            schedule_restart
        )

        if mqtt_service:
            mqtt_service.subscribe("", "mqttDevice",device_set_value)
        

        await schedule_restart()

    async def stop(cls):
        services: ObservableDict = servicesDataPoll.get(SERVICE_POLL)
        mqtt_service: Optional[MqttService] = services.get(MQTT_SERVICE_PATH)
        if mqtt_service:
            mqtt_service.unsubscribe("", "mqttDevice")
        await super().stop()
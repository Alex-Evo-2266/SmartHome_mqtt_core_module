# import json
# import logging
# from app.ingternal.device.arrays.DevicesArray import DevicesArray
# from app.ingternal.device.interface.device_class import IDevice
# from app.ingternal.device.schemas.enums import ReceivedDataFormat
# from .settings import MQTT_DEVICE_CLASS

# # Настройка логирования
# logger = logging.getLogger(__name__)

# async def device_set_value(topik, value):


#     logger.info("Processing MQTT message...")

#     try:
#         # Получаем все устройства
#         devices = DevicesArray.all()
#         if not devices:
#             logger.warning("No devices found in DevicesArray")
#             return

#         for device_cond in devices:
#             device: IDevice = device_cond.device
#             class_device = device.get_class()
#             address_device = device.get_address()
#             type_message = device.get_type_command()

#             if class_device != MQTT_DEVICE_CLASS:
#                 continue

#             fields = device.get_fields()
#             if not fields:
#                 logger.warning(f"Device {address_device} has no fields, skipping...")
#                 continue

#             data = value

#             if type_message == ReceivedDataFormat.JSON:
#                 logger.info(f"Processing JSON message for device {address_device}")
#                 print("p5600 3")
#                 # Получаем данные из токена
#                 if data is None or address_device != topik:
#                     logger.warning(f"No data extracted for device {address_device}, skipping...")
#                     continue
#                 print("p5600 4", data)

#                 try:
#                     json_data = json.loads(data)
#                 except json.JSONDecodeError:
#                     logger.error(f"Invalid JSON data for device {address_device}: {data}")
#                     continue
#                 print("p5600", fields)

#                 for field in fields:
#                     field_address = field.get_address()
#                     if field_address in json_data:
#                         new_data = json_data.get(field_address, None)
#                         if new_data is None:
#                             continue
#                         logger.info(f"Setting field {field_address} for device {address_device} to {new_data}")
#                         print("p5600 56", field_address, new_data)
#                         field.set(str(new_data))
#             elif type_message == ReceivedDataFormat.STRING:
#                 logger.info(f"Processing STRING message for device {address_device}")

#                 for field in fields:
#                     field_address = field.get_address()
#                     full_address = f"{address_device}/{field_address}"

#                     if data is None or full_address != topik:
#                         logger.warning(f"No data found for field {field_address} in device {address_device}, skipping...")
#                         continue

#                     logger.info(f"Setting field {field_address} for device {address_device} to {data}")
#                     field.set(data)
#     except Exception as e:
#         print(e)

#     logger.info("MQTT message processing complete.")
import json
from app,core.ports import dispatcher
from app.core.state.event import DeviceEvent
from app.core.state.get_store import get_container
from app.schemas.device.enums import ReceivedDataFormat
from app.pkg.logger import MyLogger

logger = MyLogger().get_logger(__name__)


def split_topic(topic: str) -> list[str]:
    return [p for p in topic.split("/") if p]


async def device_set_value(topic: str, payload: str):
    if not payload:
        logger.warning("Empty MQTT payload for topic %s", topic)
        return

    topic_parts = split_topic(topic)

    # 1️⃣ Игнорируем set
    if topic_parts and topic_parts[-1] == "set":
        logger.debug("Ignore outgoing control topic: %s", topic)
        return

    device_cond = None
    device_address_parts = None

    # 2️⃣ Ищем устройство по ПРЕФИКСУ
    for d in get_container().connect_store.all():
        addr_parts = split_topic(d.device.get_address())

        if topic_parts[:len(addr_parts)] == addr_parts:
            device_cond = d
            device_address_parts = addr_parts
            break

    if not device_cond:
        logger.warning("No device matched MQTT topic %s", topic)
        return

    device = device_cond.device
    system_name = device_cond.id

    tail = topic_parts[len(device_address_parts):]  # то, что после address
    changes = {}

    # 3️⃣ JSON payload (весь device)
    if device.get_type_command() == ReceivedDataFormat.JSON:
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                logger.warning("JSON payload is not dict: %s", payload)
                return

            changes = {k: str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload for device %s: %s", system_name, payload)
            return

    # 4️⃣ STRING payload (одно поле)
    elif device.get_type_command() == ReceivedDataFormat.STRING:
        if not tail:
            logger.warning("STRING payload but no field in topic: %s", topic)
            return

        field_address = tail[0]
        field = device.get_field_by_address(field_address)
        if not field:
            return
        changes = {field.get_name(): payload}

    if not changes:
        logger.debug("No changes parsed for device %s from topic %s", system_name, topic)
        return

    event = DeviceEvent(
        system_name=system_name,
        source="mqtt",
        changes=changes
    )

    await dispatcher.emit(event)

    logger.debug(
        "MQTT event emitted: device=%s topic=%s changes=%s",
        system_name,
        topic,
        changes
    )

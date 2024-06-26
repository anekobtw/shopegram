import os

from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils import deep_linking
from database import UsersManager
from dotenv import load_dotenv
from keyboards import get_report_kb

router = Router()


class SendForm(StatesGroup):
    message = State()


def get_deeplink(user_id: int) -> str:
    return deep_linking.create_deep_link(
        username=os.getenv("BOT_TG_NICKNAME"),
        link_type="start",
        payload=user_id,
    )


@router.message(F.text, Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer(text="Операция отменена.", reply_markup=types.ReplyKeyboardRemove())


@router.message(CommandStart(deep_link=True))
async def cmd_start_help(message: types.Message, command: CommandObject, state: FSMContext):
    UsersManager().create_user(message.from_user.id)

    if UsersManager().is_banned(message.from_user.id):
        await message.answer("К сожалению, ты был забанен.")
        return
    await state.update_data(receiver_id=int(command.args))
    await state.set_state(SendForm.message)
    await message.answer(
        "Отправь мне текст, который хочешь отправить пользователю. Не забывай про /rules\n/cancel для отмены"
    )


@router.message(CommandStart(deep_link=False))
async def start(message: types.Message):
    UsersManager().create_user(message.from_user.id)
    text = (
        f"Привет, {message.from_user.full_name}! Это бот для отправки анонимных сообщений.",
        "Помни, что пользуясь ботом, ты соглашаешься следовать /rules\n\n",
        "Отправь свою ссылку друзьям и получи сообщения от них анонимные сообщения:\n",
        f"{get_deeplink(message.from_user.id)}",
    )
    await message.answer("".join(text))


@router.message(F.text, Command("link"))
async def link(message: types.Message):
    await message.answer(
        f"Твоя личная ссылка, отправляй её друзьям:\n{get_deeplink(message.from_user.id)}"
    )


@router.message(F.text, Command("rules"))
async def rules(message: types.Message):
    text = (
        "<b>0.</b> Незнание правил не освобождает от ответственности.\n",
        "<b>1.</b> Запрещено отправлять сообщения, содержащие угрозу, сексуальный характер, вымогательство, шантаж, оскорбления, или унижения.\n",
        "<b>2.</b> При нарушении правил, пользователь будет забанен и не будет иметь возможности отправлять сообщения.\n",
        "<b>3.</b> Пользователь будет забанен только в том случае, если на его сообщение поступила жалоба. В противном случае (если человек, получиваший сообщение не пожалуется), ничего не будет.",
    )
    await message.answer("".join(text))


@router.message(F.text, Command("stats"))
async def stats(message: types.Message):
    user = UsersManager().get_user(message.from_user.id)
    ban_status = "Забанен" if user[3] == 1 else "Не забанен"
    await message.answer(
        f"<b>{message.from_user.full_name}</b>\n\nОтправлено сообщений: {user[1]}\nПолучено сообщений: {user[2]}\nСтатус: {ban_status}"
    )


@router.message(SendForm.message)
async def process_message(message: types.Message, state: FSMContext):
    if message.text is None:
        await message.answer("Произошла ошибка. Помни, что отправлять можно только текст и эмодзи.")
        await state.clear()
        return

    user_data = await state.get_data()
    await message.bot.send_message(
        chat_id=user_data["receiver_id"],
        text=f"<b>У тебя новое сообщение!</b>\n\n{message.text}",
        reply_markup=get_report_kb(message.from_user.id),
    )

    UsersManager().user_sent_message(message.from_user.id)
    UsersManager().user_received_message(user_data["receiver_id"])

    await state.clear()
    await message.answer("Отправлено!")

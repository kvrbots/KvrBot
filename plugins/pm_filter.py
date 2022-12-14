# Kanged From @TroJanZheX
import asyncio
import re
import ast

from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, DELETE_TIME, P_TTI_SHOW_OFF, IMDB, REDIRECT_TO, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, START_IMAGE_URL, UNAUTHORIZED_CALLBACK_TEXT, redirected_env
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}
FILTER_MODE = {}

@Client.on_message(filters.command('autofilter'))
async def fil_mod(client, message): 
      mode_on = ["yes", "on", "true"]
      mode_of = ["no", "off", "false"]

      try: 
         args = message.text.split(None, 1)[1].lower() 
      except: 
         return await message.reply("**πΈπ½π²πΎπΌπΏπ»π΄ππ΄ π²πΎπΌπΌπ°π½π³...**")
      
      m = await message.reply("**ππ΄πππΈπ½πΆ.../**")

      if args in mode_on:
          FILTER_MODE[str(message.chat.id)] = "True" 
          await m.edit("**π°πππΎπ΅πΈπ»ππ΄π π΄π½π°π±π»π΄π³**")
      
      elif args in mode_of:
          FILTER_MODE[str(message.chat.id)] = "False"
          await m.edit("**π°πππΎπ΅πΈπ»ππ΄π π³πΈππ°π±π»π΄π³**")
      else:
          await m.edit("πππ΄ :- /autofilter on πΎπ /autofilter off")

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client,message):
    group_id = message.chat.id
    name = message.text

    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await message.reply_text(reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await message.reply_text(
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button)
                            )
                    elif btn == "[]":
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or ""
                        )
                    else:
                        button = eval(btn) 
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button)
                        )
                except Exception as e:
                    print(e)
                break 

    else:
        if FILTER_MODE.get(str(message.chat.id)) == "False":
            return
        else:
            await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer("You are using one of my old messages, please send the request again.", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    pre = 'Chat' if settings['redirect_to'] == 'Chat' else 'files'

    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"π [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                )
            ] 
            for file in files
        ]
    else:
        btn = [        
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f'{pre}_#{file.file_id}#{query.from_user.id}',
                )
            ] 
            for file in files
        ]

    btn.insert(0, 
        [
            InlineKeyboardButton(f'β¨οΈ {search} β¨οΈ ', 'dupe')
        ]
    )
    btn.insert(1,
        [ 
            InlineKeyboardButton(f'α΄α΄α΄ Ιͺα΄s', 'dupe'),
            InlineKeyboardButton(f'sα΄ΚΙͺα΄s', 'dupe'),
            InlineKeyboardButton(f'α΄Ιͺα΄s', 'tips')
        ]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("βͺ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"π Pages {round(int(offset) / 10) + 1} / {round(total / 10)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"π {round(int(offset) / 10) + 1} / {round(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("NEXT β©", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("βͺ BACK", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"π {round(int(offset) / 10) + 1} / {round(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("NEXT β©", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("π²ππΊππππΊππΊππ π²πΎπΊππΌπ π’ππΎππΊπ½πΊ π¬ππππΎ", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.message_id)
    if not movies:
        return await query.answer("π±πΎπππΎππ π ππΊππ π£ππ½πΎ, π₯πππΎ π«πππ πΎπππππΎπ½.", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('π­ππΊπ π¬ππππΎ πππ π³ππΊπππΊππΎ π»ππ...')
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit('This Movie Not Found In DataBase')
            await asyncio.sleep(10)
            await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('Piracy Is Crime')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('Piracy Is Crime')

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('ππΊπππππππΊπ πΊπππΎ')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == "creator") or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == "creator") or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode="md"
        )
        return await query.answer('Piracy Is Crime')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode="md")
        return await query.answer('Piracy Is Crime')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('Piracy Is Crime')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)                                                      
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False 
                )
                await query.answer('π¨ ππΊππΎ ππΎππ½ πππ πΏπππΎπ π―πΎπππππΊππ , π’ππΎπΌπ ππ ππ', show_alert=True)
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    
    elif query.data.startswith("Chat"):
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
            size = size
            mention = mention
        if f_caption is None:
            f_caption = f"{files.file_name}"
            size = f"{files.file_size}"
            mention = f"{query.from_user.mention}"
  
        try:
            msg = await client.send_cached_media(
                chat_id=AUTH_CHANNEL,
                file_id=file_id,
                caption=f'<b>Hai π {query.from_user.mention}</b> π\n\n<code>[evaenmariyabot] {title}</code>\n\nβ οΈ <i>This file will be deleted from here within 5 minute as it has copyright ... !!!</i>\n\n<i>ΰ΄ΰ΅ΰ΄ͺΰ΅ΰ΄ͺΰ΄Ώΰ΄±ΰ΅ΰ΄±ΰ΅ΰ΄±ΰ΅ ΰ΄ΰ΄³ΰ΅ΰ΄³ΰ΄€ΰ΅ΰ΄ΰ΅ΰ΄£ΰ΅ΰ΄ΰ΅ ΰ΄«ΰ΄―ΰ΅½ 5 ΰ΄?ΰ΄Ώΰ΄¨ΰ΄Ώΰ΄±ΰ΅ΰ΄±ΰ΄Ώΰ΄¨ΰ΅ΰ΄³ΰ΅ΰ΄³ΰ΄Ώΰ΅½ ΰ΄ΰ΄΅ΰ΄Ώΰ΄ΰ΅ΰ΄¨ΰ΄Ώΰ΄¨ΰ΅ΰ΄¨ΰ΅ΰ΄ ΰ΄‘ΰ΄Ώΰ΄²ΰ΅ΰ΄±ΰ΅ΰ΄±ΰ΅ ΰ΄ΰ΄ΰ΅ΰ΄¨ΰ΅ΰ΄¨ΰ΄€ΰ΄Ύΰ΄£ΰ΅ ΰ΄ΰ΄€ΰ΅ΰ΄ΰ΅ΰ΄£ΰ΅ΰ΄ΰ΅ ΰ΄ΰ΄΅ΰ΄Ώΰ΄ΰ΅ ΰ΄¨ΰ΄Ώΰ΄¨ΰ΅ΰ΄¨ΰ΅ΰ΄ ΰ΄?ΰ΄±ΰ΅ΰ΄±ΰ΅ΰ΄΅ΰ΄Ώΰ΄ΰ΅ΰ΄ΰ΅ΰ΄ΰ΅ΰ΄ΰ΅ΰ΄ΰ΄Ώΰ΄²ΰ΅ΰ΄ ΰ΄?ΰ΄Ύΰ΄±ΰ΅ΰ΄±ΰ΄Ώΰ΄―ΰ΄€ΰ΄Ώΰ΄¨ΰ΅ ΰ΄Άΰ΅ΰ΄·ΰ΄ ΰ΄‘ΰ΅ΰ΅Ίΰ΄²ΰ΅ΰ΄‘ΰ΅ ΰ΄ΰ΅ΰ΄―ΰ΅ΰ΄―ΰ΅ΰ΄!</i>\n\n<i><b>β‘ Powered by {query.message.chat.title}</b></i>',
                protect_content=True if ident == "filep" else False 
            )
            msg1 = await query.message.reply(
                f'<b> Hai π {query.from_user.mention} </b>π\n\n<b>π« Your File is Ready</b>\n\n'           
                f'<b>π FΙͺΚα΄ Nα΄α΄α΄</b> : <code>[evaenmariyabot] {title}</code>\n\n'              
                f'<b>βοΈ FΙͺΚα΄ SΙͺα΄’α΄</b> : <b>{size}</b>',
                True,
                'html',
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton('π₯ π£ππππππΊπ½ π«πππ π₯ ', url = msg.link)
                        ],                       
                        [
                            InlineKeyboardButton("β οΈ π’πΊπ'π π πΌπΌπΎππ β π’πππΌπ π§πΎππΎ β οΈ", url=f'https://t.me/boysupport')
                        ]
                    ]
                )
            )
            await query.answer('Check Out The Chat',)
            await asyncio.sleep(300)
            await msg1.delete()
            await msg.delete()
            del msg1, msg
        except Exception as e:
            logger.exception(e, exc_info=True)
            await query.answer(f"Encountering Issues", True)

    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("I Like Your Smartness, But Don't Be Oversmart π", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
                size = size
                mention = mention
        if f_caption is None:
            f_caption = f"{title}"
        if size is None:
            size = f"{size}"
        if mention is None:
            mention = f"{mention}"
       

        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )
    elif query.data == "pages":
        await query.answer()
    elif query.data == "start":
        buttons = [[
        InlineKeyboardButton('ππ¬πΈ π¬ππππΎ π¦ππππ π', url=f'http://t.me/{temp.U_NAME}?startgroup=true') ] ,
     [
        InlineKeyboardButton('α΄Κα΄α΄α΄', callback_data='about_menu'),
        InlineKeyboardButton('α΄Κα΄sα΄', callback_data='close')
    ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        if not START_IMAGE_URL:
            await query.message.reply(
                script.START_TXT.format(
                    query.from_user.mention, 
                    temp.U_NAME, 
                    temp.B_NAME,
                ),
                reply_markup=reply_markup
            )
        else:
            await query.message.reply_photo(
                photo=START_IMAGE_URL,
                caption=script.START_TXT.format(
                    query.from_user.mention , 
                    temp.U_NAME, 
                    temp.B_NAME,
                ),
                reply_markup=reply_markup
            )
        await query.answer('Lα΄α΄α΄ΙͺΙ΄Ι’..........')
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('π₯ππππΎπ', callback_data='hud'),
            InlineKeyboardButton('π¨ππ½π»', callback_data='imbd'),
            InlineKeyboardButton('π’ππππΎπΌππππ', callback_data='coct')
            ],[
            InlineKeyboardButton('π₯ππ', callback_data='fun'),
            InlineKeyboardButton('π π»πππ', callback_data='about_menu'),
            InlineKeyboardButton('π²ππΊπππ', callback_data='stats')
            ],[
            InlineKeyboardButton('π‘πΊππ', callback_data='ban'),
            InlineKeyboardButton('π’ππππ½', callback_data='covid'),
            InlineKeyboardButton('π―ππ', callback_data='pin')
            ],[
            InlineKeyboardButton('π¨ππΏπ', callback_data='info'),
            InlineKeyboardButton('π©πππ', callback_data='json'),
            InlineKeyboardButton('π’πΊππ»ππ', callback_data='carbon')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode='html'
          )
    elif query.data == "about":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgQAAxkBAAECr4hiKhTf1qJEeLctIJCsrxk2k5BPmQADEgAC4oetNCxmTn2LSYe8HgQ',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('α΄Κα΄α΄α΄', callback_data='about_menu')
                    ],
                    [
                        InlineKeyboardButton('Κα΄α΄α΄', callback_data='start'),
                        InlineKeyboardButton('α΄Κα΄sα΄', callback_data='close')
                    ]
                ]
            )
        )
    elif query.data == "about_menu":
        buttons = [[
        InlineKeyboardButton('Κα΄α΄', url='https://t.me/MkTgBots'),
        InlineKeyboardButton('sα΄α΄α΄α΄Κα΄', url='https://t.me/boysupport'),
        InlineKeyboardButton('Κα΄α΄α΄', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
    elif query.data == "weather":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.WEATHER_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "cntry":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CNTRY_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('π©βπ¦― Back', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
                text=script.SOURCE_TXT,
                reply_markup=reply_markup,
                parse_mode='html'
            )
    elif query.data == "gtrans":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.GTRANS_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "urlshrt":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SHORT_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "trnt":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TRNT_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "tts":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TTS_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "mute":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MUTE_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "tts":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TTS_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "song":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SONG_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "json":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.JSON_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "covid":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.COVID_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )         
    elif query.data == "ping":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PING_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "fun":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FUN_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "ban":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BAN_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "purge":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PURGE_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "tgraph":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TGRAPH_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )       
    elif query.data == "info":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.INFO_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "imbd":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.IMBD_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "hud":
        buttons = [[
            InlineKeyboardButton('π πππ', callback_data='autofilter'),
            InlineKeyboardButton('π¬πΊπππΊπ', callback_data='manual')
            ],[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help'),
            InlineKeyboardButton('π’ππππΎ', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FILTER_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "manual":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='hud'),
            InlineKeyboardButton('π‘πππππ', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='manual')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "paste":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PASTE_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='hud')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "pin":
        buttons = [[
            InlineKeyboardButton('π‘πΊπΌπ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PIN_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('Κα΄α΄α΄', callback_data='help'),
            InlineKeyboardButton('α΄α΄α΄ΙͺΙ΄', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('Κα΄α΄α΄', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('π©βπ¦― Back', callback_data='help'),
            InlineKeyboardButton('β»οΈ', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('π©βπ¦― Back', callback_data='help'),
            InlineKeyboardButton('β»οΈ', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer('Piracy Is Crime')

        if status == "True" or status == "Chat":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton( 'Redirect To',
                                         callback_data=f'setgs#redirect_to#{settings["redirect_to"]}#{grp_id}',),
                    InlineKeyboardButton('π€ PM' if settings["redirect_to"] == "PM" else 'π Chat',
                                         callback_data=f'setgs#redirect_to#{settings["redirect_to"]}#{grp_id}',),
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('β Yes' if settings["botpm"] else 'β No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('β Yes' if settings["file_secure"] else 'β No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('β Yes' if settings["imdb"] else 'β No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('β Yes' if settings["spell_check"] else 'β No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('β Yes' if settings["welcome"] else 'β No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    elif query.data == "close":
        await query.message.delete()
    elif query.data == 'tips':
        await query.answer("sα΄Ι΄α΄ α΄α΄ΚΚα΄α΄α΄ α΄α΄α΄ Ιͺα΄/sα΄ΚΙͺα΄s Ι΄α΄α΄α΄ ?α΄Κ Κα΄α΄α΄α΄Κ Κα΄sα΄Κα΄s .\nα΄α΄ Ι’α΄α΄ Κα΄α΄α΄α΄Κ Κα΄sα΄Κα΄ ?α΄Κ sα΄ΚΙͺα΄s sα΄α΄Κα΄Κ ΚΙͺα΄α΄ α΄xα΄α΄α΄Κα΄ Ι’Ιͺα΄ α΄Ι΄, Eg - Peaky Blinders S01E01\n\n Β© EVA enmariya bot", True)
    try: await query.answer('Your Results are there in Filter Button') 
    except: pass


async def auto_filter(client, msg: pyrogram.types.Message, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    
    pre = 'filep' if settings['file_secure'] else 'file'
    pre = 'Chat' if settings['redirect_to'] == 'Chat' else pre

    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                        text=f"π [{get_size(file.file_size)}] {file.file_name}", 
                        callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}'
                )
            ] 
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}",
                    callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}',
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f'{pre}_#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}',
                )
            ]
            for file in files
        ]

    btn.insert(0, 
        [
            InlineKeyboardButton(f'β¨οΈ {search} β¨οΈ ', 'dupe')
        ]
    )
    btn.insert(1,
        [
            InlineKeyboardButton(f'α΄α΄α΄ Ιͺα΄s', 'dupe'),
            InlineKeyboardButton(f'sα΄ΚΙͺα΄s', 'dupe'),
            InlineKeyboardButton(f'α΄Ιͺα΄s', 'tips')
        ]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.message_id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"π 1/{round(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="NEXT β©", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="π 1/1", callback_data="pages")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            mention_bot=temp.MENTION,
            mention_user=message.from_user.mention if message.from_user else message.sender_chat.title,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>Hai π {message.from_user.mention}</b> π\n\n<b>π Found β¨  Files For Your Query : {search} π</b> "
    if imdb and imdb.get('poster'):
        try:
            fmsg = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            fmsg = await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            fmsg = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    else:
        fmsg = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    
    await asyncio.sleep(DELETE_TIME)
    await fmsg.delete()

    if spoll:
        await msg.message.delete()


async def advantage_spell_chok(msg):
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        k = await msg.reply("π¨ πΌπΊππ πΏπππ½ ππ ππ ππ π£πΊππΊπ‘πΊππΎ.")
        await asyncio.sleep(8)
        await k.delete()
        return
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(
        r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)',
        '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*",
                         re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match:
                gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates https://stackoverflow.com/a/7961425
    if len(gs_parsed) > 3:
        gs_parsed = gs_parsed[:3]
    if gs_parsed:
        for mov in gs_parsed:
            imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
            if imdb_s:
                movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        k = await msg.reply("π‘ππ, π’ππΎπΌπ πππΎ πππΎπππππ πΈππ ππΊππΎ ππΎππ½ ππ ππππππΎ. π¨πΏ πΈππ ππΊππΎ ππΎπππΎπππΎπ½ π₯ππ π’πΊπ πππππ πΈππ ππππ πππ π¦πΎπ ππ.")
        await asyncio.sleep(8)
        await k.delete()
        return
    SPELL_CHECK[msg.message_id] = movielist
    btn = [InlineKeyboardButton("πΙ’α΄α΄Ι’Κα΄π", url=f'https://google.com/search?q={query}')]
    await msg.reply("π‘ππ, π’ππΎπΌπ πππΎ πππΎπππππ πΈππ ππΊππΎ ππΎππ½ ππ ππππππΎ. π¨πΏ πΈππ ππΊππΎ ππΎπππΎπππΎπ½ π₯ππ π’πΊπ πππππ πΈππ ππππ πππ π¦πΎπ ππ.",
                    reply_markup=InlineKeyboardMarkup(btn))

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False

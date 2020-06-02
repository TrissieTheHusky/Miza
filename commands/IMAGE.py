try:
    from common import *
except ModuleNotFoundError:
    import os
    os.chdir("..")
    from common import *

import nekos


class IMG(Command):
    min_level = 0
    min_display = "0~2"
    description = "Sends an image in the current chat from a list."
    usage = "<tags[]> <url[]> <verbose(?v)> <random(?r)> <add(?a)> <delete(?d)> <hide(?h)>"
    flags = "vraedh"
    no_parse = True

    async def __call__(self, bot, flags, args, argv, guild, perm, **void):
        update = self.data.images.update
        imglists = bot.data.images
        images = imglists.get(guild.id, {})
        if "a" in flags or "e" in flags or "d" in flags:
            req = 2
            if perm < req:
                reason = "to change image list for " + guild.name
                raise self.permError(perm, req, reason)
            if "a" in flags or "e" in flags:
                lim = 32 << bot.isTrusted(guild.id) * 2 + 1
                if len(images) > lim:
                    raise OverflowError(
                        "Image list for " + guild.name
                        + " has reached the maximum of " + str(lim) + " items. "
                        + "Please remove an item to add another."
                    )
                key = " ".join(args[:-1]).lower()
                if len(key) > 64:
                    raise ArgumentError("Image tag too long.")
                url = await bot.followURL(verifyURL(args[-1]))
                if len(url) > 256:
                    raise ArgumentError("Image url too long.")
                images[key] = url
                sort(images)
                imglists[guild.id] = images
                update()
                if not "h" in flags:
                    return (
                        "```css\nSuccessfully added [" + noHighlight(key)
                        + "] to the image list for [" + noHighlight(guild.name) + "].```"
                    )
            if not args:
                imglists[guild.id] = {}
                update()
                return (
                    "```css\nSuccessfully removed all images from the image list for ["
                    + noHighlight(guild.name) + "].```"
                )
            key = argv.lower()
            images.pop(key)
            imglists[guild.id] = images
            update()
            return (
                "```css\nSuccessfully removed [" + noHighlight(key)
                + "] from the image list for [" + noHighlight(guild.name) + "].```"
            )
        if not argv and not "r" in flags:
            if images:
                if "v" in flags:
                    key = lambda x: x
                else:
                    key = lambda x: limStr(x, 32)
                return (
                    "Available images in **" + guild.name
                    + "**: ```ini\n" + strIter(images, key=key).replace("'", '"') + "```"
                )
            return (
                "```ini\nImage list for [" + noHighlight(guild.name)
                + "] is currently empty.```"
            )
        sources = []
        for tag in args:
            t = tag.lower()
            if t in images:
                sources.append(images[t])
        r = flags.get("r", 0)
        for _ in loop(r):
            sources.append(images[tuple(images)[xrand(len(images))]])
        if not len(sources):
            raise LookupError("Target image " + argv + " not found. Use img for list.")
        v = xrand(len(sources))
        url = sources[v]
        if "v" in flags:
            return url
        emb = discord.Embed(
            url=url,
            colour=randColour(),
        )
        emb.set_image(url=url)
        return {
            "embed": emb
        }


class CreateEmoji(Command):
    server_only = True
    name = ["EmojiCreate", "EmojiCopy", "CopyEmoji", "Emoji"]
    min_level = 2
    description = "Creates a custom emoji from a URL or attached file."
    usage = "<1:name> <0:url{attached_file}>"
    flags = "ae"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        if message.attachments:
            args = [a.url for a in message.attachments] + args
            argv = " ".join(a.url for a in message.attachments) + " " * bool(argv) + argv
        if not args:
            raise ArgumentError("Please enter URL, emoji, or attached file to add.")
        url = args.pop(-1)
        url = await bot.followURL(url)
        if not isURL(url):
            emojis = findEmojis(argv) + findEmojis(url)
            if not emojis:
                raise ArgumentError("Please enter URL, emoji, or attached file to add.")
            s = emojis[0]
            name = argv[:argv.index(s)].strip()
            s = s[2:]
            i = s.index(":")
            e_id = s[i + 1:s.rindex(">")]
            url = "https://cdn.discordapp.com/emojis/" + e_id + ".png?v=1"
        else:
            name = " ".join(args).strip()
        if not name:
            name = "emoji_" + str(len(guild.emojis))
        print(name, url)
        resp = await create_future(requests.get, url, headers={"user-agent": "Mozilla/5." + str(xrand(1, 10))}, timeout=8)
        image = resp.content
        if len(image) > 67108864:
            raise OverflowError("Max file size to load is 64MB.")
        if len(image) > 262144:
            path = "cache/" + str(guild.id) + ".png"
            f = await create_future(open, path, "wb")
            await create_future(f.write, image)
            await create_future(f.close)
            resp = await imageProc(path, "resize_max", [128], guild.id)
            fn = resp[0]
            f = await create_future(open, fn, "rb")
            image = await create_future(f.read)
            create_future_ex(f.close)
        emoji = await guild.create_custom_emoji(image=image, name=name, reason="CreateEmoji command")
        await message.add_reaction(emoji)
        return (
           "```css\nSuccessfully created emoji [" + noHighlight(emoji) + "] in ["
            + noHighlight(guild.name) + "].```"
        )


async def get_image(bot, message, args, argv):
    if message.attachments:
        args = [a.url for a in message.attachments] + args
        argv = " ".join(a.url for a in message.attachments) + " " * bool(argv) + argv
    if not args:
        raise ArgumentError("Please input an image by URL or attachment.")
    url = args.pop(0)
    url = await bot.followURL(url)
    if not isURL(url):
        emojis = findEmojis(argv) + findEmojis(url)
        if not emojis:
            raise ArgumentError("Please input an image by URL or attachment.")
        s = emojis[0]
        value = argv[argv.index(s) + len(s):].strip()
        s = s[2:]
        i = s.index(":")
        e_id = s[i + 1:s.rindex(">")]
        url = "https://cdn.discordapp.com/emojis/" + e_id + ".png?v=1"
    else:
        value = " ".join(args).strip()
    if not value:
        value = 2
    else:
        value = await bot.evalMath(value, message.guild.id)
        if not value >= -16 or not value <= 16:
            raise OverflowError("Maximum multiplier input is 16.")
    try:
        name = url[url.rindex("/") + 1:]
        if not name:
            raise ValueError
        if "." in name:
            name = name[:name.rindex(".")]
    except ValueError:
        name = "unknown"
    if "." not in name:
        name += ".png"
    return name, value, url


class Saturate(Command):
    name = ["Saturation", "ImageSaturate"]
    min_level = 0
    description = "Changes colour saturation of supplied image."
    usage = "<0:url{attached_file}> <1:multiplier[2]>"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        name, value, url = await get_image(bot, message, args, argv)
        resp = await imageProc(url, "Enhance", ["Color", value], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class Contrast(Command):
    name = ["ImageContrast"]
    min_level = 0
    description = "Changes colour contrast of supplied image."
    usage = "<0:url{attached_file}> <1:multiplier[2]>"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        name, value, url = await get_image(bot, message, args, argv)
        resp = await imageProc(url, "Enhance", ["Contrast", value], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class Brightness(Command):
    name = ["Brighten", "ImageBrightness"]
    min_level = 0
    description = "Changes colour brightness of supplied image."
    usage = "<0:url{attached_file}> <1:multiplier[2]>"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        name, value, url = await get_image(bot, message, args, argv)
        resp = await imageProc(url, "Enhance", ["Brightness", value], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class Sharpness(Command):
    name = ["Sharpen", "ImageSharpness"]
    min_level = 0
    description = "Changes colour sharpness of supplied image."
    usage = "<0:url{attached_file}> <1:multiplier[2]>"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        name, value, url = await get_image(bot, message, args, argv)
        resp = await imageProc(url, "Enhance", ["Sharpness", value], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class HueShift(Command):
    name = ["Hue"]
    min_level = 0
    description = "Changes colour hue of supplied image."
    usage = "<0:url{attached_file}> <1:adjustment[0.5]>"
    no_parse = True
    rate_limit = 3

    async def __call__(self, bot, guild, message, args, argv, **void):
        name, value, url = await get_image(bot, message, args, argv)
        resp = await imageProc(url, "hue_shift", [value], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class Colour(Command):
    name = ["Color"]
    min_level = 0
    description = "Creates a 128x128 image filled with the target RGB colour."
    usage = "<Colour>"
    no_parse = True
    rate_limit = 2

    async def __call__(self, bot, guild, channel, argv, **void):
        argv = argv.replace("#", "").replace(",", " ").strip()
        if " " in argv:
            channels = [i.strip() for i in argv.split(" ") if i.strip()]
            if len(channels) not in (3, 4):
                raise ArgumentError("Please input valid amount of colours for RGB/RGBA input.")
        else:
            try:
                raw = int(argv, 16)
                if len(argv) <= 6:
                    channels = [raw >> 16 & 255, raw >> 8 & 255, raw & 255]
                elif len(argv) <= 8:
                    channels = [raw >> 16 & 255, raw >> 8 & 255, raw & 255, raw >> 24 & 255]
                else:
                    raise ValueError
            except ValueError:
                raise ArgumentError("Please input a valid hex colour.")
        resp = await imageProc("from_colour", "$", [channels], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename="colour.png")
        await sendFile(channel, "", f)


class Resize(Command):
    name = ["ImageScale", "Scale", "ImageResize"]
    min_level = 0
    description = "Changes size of supplied image, using an optional scaling operation."
    usage = "<0:url{attached_file}> <1:x_multiplier[0.5]> <2:y_multiplier[x]> <3:operation[auto](?l)>"
    no_parse = True
    rate_limit = 3
    flags = "l"

    async def __call__(self, bot, guild, message, flags, args, argv, **void):
        if message.attachments:
            args = [a.url for a in message.attachments] + args
            argv = " ".join(a.url for a in message.attachments) + " " * bool(argv) + argv
        if not args:
            if "l" in flags:
                return (
                    "```ini\nAvailable scaling operations: ["
                    + "nearest, linear, hamming, bicubic, lanczos, auto]```"
                )
            raise ArgumentError("Please input an image by URL or attachment.")
        url = args.pop(0)
        url = await bot.followURL(url)
        if not isURL(url):
            emojis = findEmojis(argv) + findEmojis(url)
            if not emojis:
                raise ArgumentError("Please input an image by URL or attachment.")
            s = emojis[0]
            value = argv[argv.index(s) + len(s):].strip()
            s = s[2:]
            i = s.index(":")
            e_id = s[i + 1:s.rindex(">")]
            url = "https://cdn.discordapp.com/emojis/" + e_id + ".png?v=1"
        else:
            value = " ".join(args).strip()
        if not value:
            x = y = 0.5
            op = "auto"
        else:
            value = value.replace("x", " ").replace("X", " ").replace("*", " ").replace("×", " ")
            try:
                spl = shlex.split(value)
            except ValueError:
                spl = value.split()
            x = await bot.evalMath(spl.pop(0), message.guild.id)
            if spl:
                y = await bot.evalMath(spl.pop(0), message.guild.id)
            else:
                y = x
            for value in (x, y):
                if not value >= -16 or not value <= 16:
                    raise OverflowError("Maximum multiplier input is 16.")
            if spl:
                op = " ".join(spl)
            else:
                op = "auto"
        try:
            name = url[url.rindex("/") + 1:]
            if not name:
                raise ValueError
            if "." in name:
                name = name[:name.rindex(".")]
        except ValueError:
            name = "unknown"
        if "." not in name:
            name += ".png"
        resp = await imageProc(url, "resize_mult", [x, y, op], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class Blend(Command):
    name = ["ImageBlend", "ImageOP"]
    min_level = 0
    description = "Combines the two supplied images, using an optional blend operation."
    usage = "<0:url1{attached_file}> <1:url2{attached_file}> <2:operation[replace](?l)> <3:opacity[1]>"
    no_parse = True
    rate_limit = 4
    flags = "l"

    async def __call__(self, bot, guild, message, flags, args, argv, **void):
        if message.attachments:
            args = [a.url for a in message.attachments] + args
            argv = " ".join(a.url for a in message.attachments) + " " * bool(argv) + argv
        if not args:
            if "l" in flags:
                return (
                    "```ini\nAvailable blend operations: ["
                    + "replace, add, sub, mul, div, mod, and, or, xor, nand, nor, xnor, "
                    + "difference, overlay, screen, soft, hard, lighten, darken, "
                    + "burn, linearburn, dodge, lineardodge, hue, sat, lum, extract, merge]```"
                )
            raise ArgumentError("Please input an image by URL or attachment.")
        url1 = args.pop(0)
        url1 = await bot.followURL(url1)
        url2 = args.pop(0)
        url2 = await bot.followURL(url2)
        fromA = False
        if not isURL(url1):
            emojis = findEmojis(argv) + findEmojis(url1)
            if not emojis:
                raise ArgumentError("Please input an image by URL or attachment.")
            s = emojis[0]
            argv = argv[argv.index(s) + len(s):].strip()
            s = s[2:]
            i = s.index(":")
            e_id = s[i + 1:s.rindex(">")]
            url1 = "https://cdn.discordapp.com/emojis/" + e_id + ".png?v=1"
            fromA = True
        if not isURL(url2):
            emojis = findEmojis(argv) + findEmojis(url2)
            if not emojis:
                raise ArgumentError("Please input an image by URL or attachment.")
            s = emojis[0]
            argv = argv[argv.index(s) + len(s):].strip()
            s = s[2:]
            i = s.index(":")
            e_id = s[i + 1:s.rindex(">")]
            url1 = "https://cdn.discordapp.com/emojis/" + e_id + ".png?v=1"
            fromA = True
        if fromA:
            value = argv
        else:
            value = " ".join(args).strip()
        if not value:
            opacity = 1
            operation = "replace"
        else:
            try:
                spl = shlex.split(value)
            except ValueError:
                spl = value.split()
            operation = spl.pop(0)
            if spl:
                opacity = await bot.evalMath(spl.pop(-1), message.guild.id)
            else:
                opacity = 1
            if not opacity >= -16 or not opacity <= 16:
                raise OverflowError("Maximum multiplier input is 16.")
            if spl:
                operation += " ".join(spl)
            if not operation:
                operation = "replace"
        try:
            name = url1[url1.rindex("/") + 1:]
            if not name:
                raise ValueError
            if "." in name:
                name = name[:name.rindex(".")]
        except ValueError:
            name = "unknown"
        if "." not in name:
            name += ".png"
        resp = await imageProc(url1, "blend_op", [url2, operation, opacity], guild.id)
        fn = resp[0]
        f = discord.File(fn, filename=name)
        await sendFile(message.channel, "", f)


class React(Command):
    server_only = True
    name = ["AutoReact"]
    min_level = 2
    description = "Causes ⟨MIZA⟩ to automatically assign a reaction to messages containing the substring."
    usage = "<0:react_to[]> <1:react_data[]> <disable(?d)>"
    flags = "aed"
    no_parse = True
    rate_limit = 1

    async def __call__(self, bot, flags, guild, message, argv, args, **void):
        update = self.data.reacts.update
        following = bot.data.reacts
        curr = setDict(following, guild.id, multiDict())
        if type(curr) is not multiDict:
            following[guild.id] = curr = multiDict(curr)
        if not argv:
            if "d" in flags:
                if guild.id in following:
                    following.pop(guild.id)
                    update()
                return "```css\nRemoved all auto reacts for [" + noHighlight(guild.name) + "].```"
            else:
                if not curr:
                    return (
                        "```ini\nNo currently active auto reacts for ["
                        + noHighlight(guild.name) + "].```"
                    )
                return (
                    "Currently active auto reacts for **" + discord.utils.escape_markdown(guild.name)
                    + "**:\n```ini\n" + strIter(curr) + "```"
                )
        if "d" in flags:
            a = reconstitute(argv).lower()
            if a in curr:
                curr.pop(a)
                update()
                return (
                    "```css\nRemoved [" + noHighlight(a) + "] from the auto react list for ["
                    + noHighlight(guild.name) + "].```"
                )
            else:
                raise LookupError(str(a) + " is not in the auto react list.")
        lim = 32 << bot.isTrusted(guild.id) * 2 + 1
        if curr.count() >= lim:
            raise OverflowError(
                "React list for " + guild.name
                + " has reached the maximum of " + str(lim) + " items. "
                + "Please remove an item to add another."
            )
        a = reconstitute(" ".join(args[:-1])).lower()[:64]
        try:
            e_id = int(args[-1])
        except:
            emoji = args[-1]
        else:
            emoji = await bot.fetch_emoji(e_id)
        await message.add_reaction(emoji)
        curr.append(a, str(emoji))
        update()
        return (
            "```css\nAdded [" + noHighlight(a) + "] ➡️ [" + noHighlight(args[1]) + "] to the auto react list for ["
            + noHighlight(guild.name) + "].```"
        )


def _c2e(string, em1, em2):
    chars = {
        " ": [0, 0, 0, 0, 0],
        "_": [0, 0, 0, 0, 7],
        "!": [2, 2, 2, 0, 2],
        '"': [5, 5, 0, 0, 0],
        ":": [0, 2, 0, 2, 0],
        ";": [0, 2, 0, 2, 4],
        "~": [0, 5, 7, 2, 0],
        "#": [10, 31, 10, 31, 10],
        "$": [7, 10, 6, 5, 14],
        "?": [6, 1, 2, 0, 2],
        "%": [5, 1, 2, 4, 5],
        "&": [4, 10, 4, 10, 7],
        "'": [2, 2, 0, 0, 0],
        "(": [2, 4, 4, 4, 2],
        ")": [2, 1, 1, 1, 2],
        "[": [6, 4, 4, 4, 6],
        "]": [3, 1, 1, 1, 3],
        "|": [2, 2, 2, 2, 2],
        "*": [21, 14, 4, 14, 21],
        "+": [0, 2, 7, 2, 0],
        "=": [0, 7, 0, 7, 0],
        ",": [0, 0, 3, 3, 4],
        "-": [0, 0, 7, 0, 0],
        ".": [0, 0, 3, 3, 0],
        "/": [1, 1, 2, 4, 4],
        "\\": [4, 4, 2, 1, 1],
        "@": [14, 17, 17, 17, 14],
        "0": [7, 5, 5, 5, 7],
        "1": [3, 1, 1, 1, 1],
        "2": [7, 1, 7, 4, 7],
        "3": [7, 1, 7, 1, 7],
        "4": [5, 5, 7, 1, 1],
        "5": [7, 4, 7, 1, 7],
        "6": [7, 4, 7, 5, 7],
        "7": [7, 5, 1, 1, 1],
        "8": [7, 5, 7, 5, 7],
        "9": [7, 5, 7, 1, 7],
        "A": [2, 5, 7, 5, 5],
        "B": [6, 5, 7, 5, 6],
        "C": [3, 4, 4, 4, 3],
        "D": [6, 5, 5, 5, 6],
        "E": [7, 4, 7, 4, 7],
        "F": [7, 4, 7, 4, 4],
        "G": [7, 4, 5, 5, 7],
        "H": [5, 5, 7, 5, 5],
        "I": [7, 2, 2, 2, 7],
        "J": [7, 1, 1, 5, 7],
        "K": [5, 5, 6, 5, 5],
        "L": [4, 4, 4, 4, 7],
        "M": [17, 27, 21, 17, 17],
        "N": [9, 13, 15, 11, 9],
        "O": [2, 5, 5, 5, 2],
        "P": [7, 5, 7, 4, 4],
        "Q": [4, 10, 10, 10, 5],
        "R": [6, 5, 7, 6, 5],
        "S": [3, 4, 7, 1, 6],
        "T": [7, 2, 2, 2, 2],
        "U": [5, 5, 5, 5, 7],
        "V": [5, 5, 5, 5, 2],
        "W": [17, 17, 21, 21, 10],
        "X": [5, 5, 2, 5, 5],
        "Y": [5, 5, 2, 2, 2],
        "Z": [7, 1, 2, 4, 7],
    }
    printed = [""] * 7
    string = string.upper()
    for i in range(len(string)):
        curr = string[i]
        data = chars.get(curr, [15] * 5)
        size = max(1, max(data))
        lim = max(2, int(log(size, 2))) + 1
        printed[0] += em2 * (lim + 1)
        printed[6] += em2 * (lim + 1)
        if len(data) == 5:
            for y in range(5):
                printed[y + 1] += em2
                for p in range(lim):
                    if data[y] & (1 << (lim - 1 - p)):
                        printed[y + 1] += em1
                    else:
                        printed[y + 1] += em2
        for x in range(len(printed)):
            printed[x] += em2
    output = "\n".join(printed)
    print("[" + em1 + "]", "[" + em2 + "]")
    if len(em1) + len(em2) > 2 and ":" in em1 + em2:
        return output
    return "```fix\n" + output + "```"


class Char2Emoj(Command):
    name = ["C2E"]
    min_level = 0
    description = "Makes emoji blocks using a string."
    usage = "<0:string> <1:emoji_1> <2:emoji_2>"

    async def __call__(self, args, **extra):
        try:
            if len(args) != 3:
                raise IndexError
            for i in range(1,3):
                if args[i][0] == ":" and args[i][-1] != ":":
                    args[i] = "<" + args[i] + ">"
            return _c2e(*args[:3])
        except IndexError:
            raise ArgumentError(
                "Exactly 3 arguments are required for this command.\n"
                + "Place <> around arguments containing spaces as required."
            )


f = open("auth.json")
auth = ast.literal_eval(f.read())
f.close()
try:
    cat_key = auth["cat_api_key"]
except:
    cat_key = None
    print("WARNING: cat_api_key not found. Unable to use API to pull cat images.")


class Cat(Command):
    is_command = True
    if cat_key:
        header = {"x-api-key": cat_key}
    else:
        header = None
    min_level = 0
    description = "Pulls a random image from thecatapi.com or cdn.nekos.life/meow, and embeds it."
    usage = "<verbose(?v)>"
    flags = "v"
    rate_limit = 0.25

    async def __call__(self, channel, flags, **void):
        if not self.header or random.random() > 0.9375:
            url = nekos.cat()
        else:
            for _ in loop(8):
                resp = await create_future(
                    requests.get,
                    "https://api.thecatapi.com/v1/images/search",
                    headers=self.header,
                    timeout=8,
                )
                try:
                    d = json.loads(resp.content)
                except:
                    d = eval(resp.content, {}, eval_const)
                try:
                    if type(d) is list:
                        d = random.choice(d)
                    url = d["url"]
                    break
                except KeyError:
                    await asyncio.sleep(0.5)
        if "v" in flags:
            text = "Pulled from " + url
            return text
        emb = discord.Embed(
            url=url,
            colour=randColour(),
        )
        emb.set_image(url=url)
        print(url)
        return {
            "embed": emb
        }


class Dog(Command):
    min_level = 0
    description = "Pulls a random image from images.dog.ceo and embeds it."
    usage = "<verbose(?v)>"
    flags = "v"
    rate_limit = 0.25

    async def __call__(self, channel, flags, **void):
        for _ in loop(8):
            resp = await create_future(
                requests.get,
                "https://dog.ceo/api/breeds/image/random",
                timeout=8,
            )
            try:
                d = json.loads(resp.content)
            except:
                d = eval(resp.content, {}, eval_const)
            try:
                if type(d) is list:
                    d = random.choice(d)
                url = d["message"]
                break
            except KeyError:
                await asyncio.sleep(0.5)
        url = url.replace("\\", "/")
        while "///" in url:
            url = url.replace("///", "//")
        if "v" in flags:
            text = "Pulled from " + url
            return text
        emb = discord.Embed(
            url=url,
            colour=randColour(),
        )
        emb.set_image(url=url)
        print(url)
        return {
            "embed": emb
        }


class UpdateImages(Database):
    name = "images"


class UpdateReacts(Database):
    name = "reacts"

    async def _nocommand_(self, text, edit, orig, message, **void):
        if message.guild is None or not orig:
            return
        g_id = message.guild.id
        data = self.data
        if g_id in data:
            try:
                following = self.data[g_id]
                if type(following) != multiDict:
                    following = self.data[g_id] = multiDict(following)
                reacting = {}
                for k in following:
                    if is_alphanumeric(k):
                        words = text.split(" ")
                    else:
                        words = message.content.lower()
                    if k in words:
                        emojis = following[k]
                        reacting[words.index(k) / len(words)] = emojis
                for r in sorted(list(reacting)):
                    for react in reacting[r]:
                        await message.add_reaction(react)
            except ZeroDivisionError:
                pass
            except:
                print(traceback.format_exc())
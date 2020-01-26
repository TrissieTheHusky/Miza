import datetime
from smath import *
    
class purge:
    is_command = True
    def __init__(self):
        self.name = ["del","delete"]
        self.minm = 1
        self.desc = "Deletes a number of messages from a certain user in current channel."
        self.usag = '<1:user:{bot}(?a)> <0:count:[1]> <hide:(?h)>'
    async def __call__(self,client,_vars,argv,args,channel,user,guild,name,flags,**void):
        t_user = -1
        if "a" in flags or "@everyone" in argv or "@here" in argv:
            t_user = None
        if len(args) < 2:
            if t_user == -1:
                t_user = client.user
            if len(args) < 1:
                count = 1
            else:
                count = round(_vars.evalMath(args[0]))
        else:
            a1 = args[0]
            a2 = " ".join(args[1:])
            count = round(_vars.evalMath(a2))
            if t_user == -1:
                t_user = await client.fetch_user(_vars.verifyID(a1))
        if t_user != client.user:
            s_perm = _vars.getPerms(user,guild)
            if s_perm < 3:
                return "Error: Insufficient priviliges for command "+name+" "+args[1]+"\
.\nRequred level: **__"+'3'+"__**, Current level: **__"+str(s_perm)+"__**"
        hist = await channel.history(limit=128).flatten()
        delM = []
        deleted = 0
        for m in hist:
            if count <= 0:
                break
            if t_user is None or m.author.id == t_user.id:
                delM.append(m)
                count -= 1
        try:
            await channel.delete_messages(delM)
            deleted = len(delM)
        except:
            for m in delM:
                try:
                    await m.delete()
                    deleted += 1
                except:
                    pass
        if not "h" in flags:
            return "Deleted **__"+str(deleted)+"__** message"+"s"*(deleted!=1)+"!"
    
class ban:
    is_command = True
    def __init__(self):
        self.name = []
        self.minm = 3
        self.desc = "Bans a user for a certain amount of hours, with an optional reason."
        self.usag = '<0:user> <1:hours[]> <2:reason[]> <hide:(?h)>'
    async def __call__(self,client,_vars,args,user,channel,guild,flags,**void):
        dtime = datetime.datetime.utcnow().timestamp()
        a1 = args[0]
        t_user = await client.fetch_user(_vars.verifyID(a1))
        s_perm = _vars.getPerms(user,guild)
        t_perm = _vars.getPerms(t_user,guild)
        if t_perm+1>=s_perm or not isValid(t_perm):
            if len(args) > 1:
                return "Error: Insufficient priviliges to ban **"+t_user.name+"** from \
**"+guild.name+"**.\nRequired level: **__"+str(t_perm+1)+"__**, Current level: **__"+str(s_perm)+"__**"
        if len(args) < 2:
            tm = 0
        else:
            tm = _vars.evalMath(args[1])
        if len(args) >= 3:
            msg = args[2]
        else:
            msg = None
        g_id = guild.id
        g_bans = _vars.bans.get(g_id,{})
        is_banned = g_bans.get(t_user.id,None)
        if is_banned is not None:
            is_banned = is_banned[0]-dtime
            if len(args) < 2:
                return "Current ban for **"+t_user.name+"** from \
**"+guild.name+"**: **__"+str(is_banned/3600)+"__** hours."
        elif len(args) < 2:
            return "**"+t_user.name+"** is currently not banned from **"+guild.name+"**."
        g_bans[t_user.id] = [tm*3600+dtime,channel.id]
        _vars.bans[g_id] = g_bans
        _vars.update()
        if tm >= 0:
            await guild.ban(t_user,reason=msg,delete_message_days=0)
        response = None
        if is_banned:
            response = "Updated ban for **"+t_user.name+"** from \
**__"+str(is_banned/3600)+"__** hours to **__"+str(tm)+"__** hours."
        elif tm >= 0:
            response = "**"+t_user.name+"** has been banned from \
**"+guild.name+"** for **__"+str(tm)+"__** hour"+"s"*(tm!=1)+"."
        if msg:
            response += " Reason: **"+msg+"**."
        if "h" not in flags:
            return response

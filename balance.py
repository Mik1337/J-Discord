import discord, json, requests, pymysql.cursors
from cogs.utils import rpc
from discord.ext import commands

#result_set = database response with parameters from query
#db_bal = nomenclature for result_set["balance"]
#author = author from message context, identical to user in database
#wallet_bal = nomenclature for wallet reponse
class rpc:

	def listtransactions(params,count):
		port = "11311"
		rpc_user = 'srf2UUR0'
		rpc_pass = 'srf2UUR0XomxYkWw'
		serverURL = 'http://localhost:'+port
		headers = {'content-type': 'application/json'}

		payload = json.dumps({"method": "listtransactions", "params": [params,count], "jsonrpc": "2.0"})
		response = requests.get(serverURL, headers=headers, data=payload, auth=(rpc_user,rpc_pass))
		return(response.json()['result'])

class Balance:

	def __init__(self, bot):
		self.bot = bot

		#//Establish connection to db//
		self.connection = pymysql.connect(
			host='localhost',
			user='root',
			password='',
			db='netcoin')
		
		self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)

	def make_user(self, author):
		print(author)
		to_exec("""
				INSERT INTO db(user,balance)
				VALUES('%s','%s')
				""")
		self.cursor.execute(to_exec, str(author), '0')
		self.connection.commit()
		return

	def check_for_user(self, author):
		try:
			to_exec("""
				SELECT user
				FROM db
				WHERE user
				LIKE '%s'
				""")
			self.cursor.execute(to_exec, str(author))
			result_set = self.cursor.fetchone()
		except Exception as e:
			print("Error in SQL query: ",str(e))
			return
		if result_set == None:
			self.make_user(author)
			return
		
	def update_db(self, author, db_bal, lastblockhash):
		try:
			to_exec("""
				UPDATE db
				SET balance='%s', lastblockhash='%s'
				WHERE user
				LIKE '%s'
				""")
			self.cursor.execute(to_exec, db_bal,lastblockhash,str(author))
			self.connection.commit()
		except Exception as e:
			print("Error: "+str(e))
		return

	async def do_embed(self, author, db_bal):
		embed = discord.Embed(colour=discord.Colour.red())
		embed.add_field(name="User", value=author)
		embed.add_field(name="Balance (NET)", value="%.8f" % round(float(db_bal),8))
		embed.set_footer(text="Sponsored by altcointrain.com - Choo!!! Choo!!!")

		try:
			await self.bot.say(embed=embed)
		except discord.HTTPException:
			await self.bot.say("I need the `Embed links` permission to send this")
		return

	async def parse_part_bal(self,result_set,author):
		params = author
		count = 1000
		get_transactions = rpc.listtransactions(params,count)
		print(len(get_transactions))
		i = len(get_transactions)-1

		new_balance = float(result_set["balance"])
		lastblockhash = get_transactions[i]["blockhash"]
		print("LBH: ",lastblockhash)
		if lastblockhash == result_set["lastblockhash"]:
			db_bal = result_set["balance"]
			await self.do_embed(author, db_bal)
			return
		else:
			while i <= len(get_transactions):
				if get_transactions[i]["blockhash"] != result_set["lastblockhash"]:
					new_balance += float(get_transactions[i]["amount"])
					i -= 1
				else:
					new_balance += float(get_transactions[i]["amount"])
					break
			db_bal = new_balance
			self.update_db(author, db_bal, lastblockhash)
			await self.do_embed(author, db_bal)

	async def parse_whole_bal(self,result_set,author):
		params = author
		user = params
		count = 1000
		get_transactions = rpc.listtransactions(params,count)
		print(len(get_transactions))
		i = len(get_transactions)-1

		if len(get_transactions) == 0:
			print("0 transactions found for "+author+", balance must be 0")
			db_bal = 0
			await self.do_embed(author, db_bal)
		else:
			new_balance = 0
			lastblockhash = get_transactions[i]["blockhash"]
			firstblockhash = get_transactions[0]["blockhash"]
			print("FBH: ",firstblockhash)
			print("LBH: ",lastblockhash)
			while i <= len(get_transactions)-1:
				if get_transactions[i]["blockhash"] != firstblockhash:
					new_balance += float(get_transactions[i]["amount"])
					i -= 1
					print("New Balance: ",new_balance)
				else:
					new_balance += float(get_transactions[i]["amount"])
					print("New Balance: ",new_balance)
					break
			db_bal = new_balance
			self.update_db(author, db_bal, lastblockhash)
			await self.do_embed(author, db_bal)
			#Now update db with new balance

	@commands.command(pass_context=True)
	async def balance(self, ctx):
		#//Set important variables//
		author = str(ctx.message.author)

		#//Check if user exists in db
		self.check_for_user(author)

		#//Execute and return SQL Query
		try:
			to_exec("""
				SELECT balance, user, lastblockhash, tipped
				FROM db
				WHERE user
				LIKE '%s'
				""")
			self.cursor.execute(to_exec,str(author))
			result_set = self.cursor.fetchone()
		except Exception as e:
			print("Error in SQL query: ",str(e))
			return
		#//
		if result_set["lastblockhash"] == "0":
			await self.parse_whole_bal(result_set,author)
		else:
			await self.parse_part_bal(result_set,author)

def setup(bot):
	bot.add_cog(Balance(bot))

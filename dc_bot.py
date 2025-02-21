import logging
import time
import boto3
import discord
from mcstatus import JavaServer
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

# YOUR CREDENTIALS
## Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # discord bot token

## AWS
### IAM
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')  # Access key of IAM account
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')  # Secret key of IAM account

### Instance
INSTANCE_ID = os.getenv('INSTANCE_ID')  # ID of the instance you want to use as a server
REGION = os.getenv('REGION')  # Region of your server

## Minecraft Server
MINECRAFT_SERVER = os.getenv('MINECRAFT_SERVER')  # Your server IP

ec2_client = boto3.client(
    "ec2",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

status = JavaServer.lookup(MINECRAFT_SERVER).status()


@bot.event
async def on_ready():
    logging.info(f'Bot {bot.user} jest online!')


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command(name="pong")
async def pong(ctx):
    await ctx.send("Ping!")


@bot.command(name="status")
async def status(ctx):
    try:
        if status.players.online > 2:
            await ctx.send(f"Aktualnie gra {status.players.online} osób. Ping to {status.latency:.1f} ms")
        elif status.players.online == 1:
            await ctx.send(f"Aktualnie gra {status.players.online} osoba. Ping to {status.latency:.1f} ms")
        elif status.players.online == 0:
            await ctx.send(f"Nikt nie gra. Ping to {status.latency:.1f} ms")
        else:
            await ctx.send(f"Aktualnie grają {status.players.online} osoby. Ping to {status.latency:.1f} ms")
        return
    except Exception as e:
        await ctx.send("Serwer nie odpowiada. Użyj komendy !start, aby włączyć serwer.")
        logging.info("Status MC: %s", e)


@bot.command(name="start")
async def start(ctx):
    """Uruchamia nową instancję EC2."""
    await ctx.send("Sprawdzam stan serwera...")
    try:
        await ctx.send("Serwer jest już online 🟢")
        return
    except Exception as e:
        await ctx.send("Serwer nie odpowiada. Uruchamiam...")
        logging.info("Status MC: %s", e)
    try:
        response = ec2_client.describe_instances(InstanceIds=[INSTANCE_ID])
        instance = response["Reservations"][0]["Instances"][0]
        state = instance["State"]["Name"]
        logging.info("Stan instancji: %s", state)
    except Exception as e:
        await ctx.send(f"Błąd przy sprawdzaniu stanu instancji: {e}")
        await ctx.send("Spróbuj ponownie za 10 minut. W tym czasie zaparz sobie kawę... ☕️")
        return

    if state == "running":
        await ctx.send("Instancja EC2 jest już uruchomiona, sprawdzam status serwera...")
        try:
            await ctx.send("Serwer jest już online 🟢")
            return
        except Exception as e:
            await ctx.send("Serwer nie odpowiada. Uruchamiam...")
            logging.info("Status MCL %s", e)

    elif state in ["stopped", "stopping"]:
        await ctx.send("Instancja EC2 jest wyłączona, uruchamiam instancję...")
        try:
            start_response = ec2_client.start_instances(InstanceIds=[INSTANCE_ID])
            starting_instances = start_response.get("StartingInstances")
            if starting_instances:
                instance_id = starting_instances[0]["InstanceId"]
                await ctx.send(f"Instancja {instance_id} została uruchomiona! Czekam na uruchomienie...")

                while True:
                    resp = ec2_client.describe_instances(InstanceIds=[INSTANCE_ID])
                    state = resp["Reservations"][0]["Instances"][0]["State"]["Name"]
                    if state == "running":
                        break
                    time.sleep(5)
                await ctx.send("Instancja uruchomiona, serwer inicjalizuje się...")
        except Exception as e:
            logging.error("Błąd przy uruchamianiu instancji: %s", e)
            await ctx.send(f"Błąd przy uruchamianiu instancji: {e}")
            await ctx.send("Spróbuj ponownie za 10 minut. W tym czasie zaparz sobie kawę... ☕️")

    else:
        await ctx.send(f"Stan instancji EC2: {state}. Nie mogę podjąć dalszych akcji.")


@bot.command(name="stop")
async def stop_server(ctx):
    """Zatrzymuje instancję EC2 o podanym ID."""
    await ctx.send("Próbuję zatrzymać instancję")
    try:
        if status.players.online == 0:
            ec2_client.stop_instances(InstanceIds=[INSTANCE_ID])
            await ctx.send("Polecenie zatrzymania dla instancji zostało wysłane.")
            await ctx.send("Serwer jest offline 🔴")
        else:
            await ctx.send("Na serwerze znajdują się gracze. Zatrzymanie serwera nie jest możliwe.")
    except Exception as e:
        logging.error("Błąd przy zatrzymywaniu instancji: %s", e)
        await ctx.send(f"Wystąpił błąd: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
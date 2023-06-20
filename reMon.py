import sys, time, math
import libvirt
from tqdm import tqdm
from datetime import datetime

def GetIntFromUser(prompt: str) -> int:
    while True:
        num = input(prompt)
        try:
            num = int(num)
            return num
        except ValueError:
            # Handle the exception
            print('Needs to be a valid interger')


## Connect to qemu
con = None
try:
    con = libvirt.open("qemu:///system")
except libvirt.libvirtError as e:
    print(repr(e), file=sys.stderr)
    exit(1)


## Get a list of VMs and have user select 1 to monitor.
vms = con.getAllDomainStats()

print(f"Detected machines:")
for i, vm in enumerate(vms):
    print(f"{i}: {vm[0].name()}")



vmInd = GetIntFromUser("Choose VM to monitor: ")

activeVM = vms[vmInd]

interval = GetIntFromUser("Interval in seconds at which data is gathered: ")
datapoints = GetIntFromUser("Data points to gather: ")
print(f"Will gather {datapoints} data points at an interval of {interval}s.")

asdasdasd = con.domainListGetStats([activeVM[0]])[0][1]
b0name = asdasdasd["block.0.name"]
netname = asdasdasd["net.0.name"]
guestcpus = len(activeVM[0].vcpus()[0])
timeStamp = time.time()
a = math.modf(timeStamp)[0]
time.sleep(1-a+0.1)

activeVM[0].setMemoryStatsPeriod(interval, libvirt.VIR_DOMAIN_AFFECT_LIVE)

stats = []
for i in tqdm(range(datapoints)):
    # statele = {}
    timeStamp = time.time()
    # domstats = con.domainListGetStats([activeVM[0]])[0][1]
    # domstats["time_stamp"] = int(timeStamp)    
    statele = activeVM[0].getCPUStats(True)[0]
    ram = activeVM[0].memoryStats()
    net = activeVM[0].interfaceStats(netname)
    drive = activeVM[0].blockStats(b0name)

    

    statele["time_stamp"] = (timeStamp)
    statele["ram_actual"] = ram["actual"]
    statele["ram_unused"] = ram["unused"]
    statele["net.0.rx.bytes"] = net[0]
    statele["net.0.tx.bytes"] = net[4]
    statele["block.0.rd.bytes"] = drive[1] # Read
    statele["block.0.wr.bytes"] = drive[3] # Write
    stats.append(statele)
    # time.sleep(interval)
    time.sleep(interval - (time.time() % 1.0))

# One last entry to such that the amount of datapoints are not off by one.
# Could add above, or even +1 in loop. But +1 in loop
# annoys me when tqdm has x/101.
timeStamp = time.time()
statele = activeVM[0].getCPUStats(True)[0]
ram = activeVM[0].memoryStats()
net = activeVM[0].interfaceStats(netname)
drive = activeVM[0].blockStats(b0name)
statele["time_stamp"] = (timeStamp)
statele["ram_actual"] = ram["actual"]
statele["ram_unused"] = ram["unused"]
statele["net.0.rx.bytes"] = net[0]
statele["net.0.tx.bytes"] = net[4]
statele["block.0.rd.bytes"] = drive[1] # Read
statele["block.0.wr.bytes"] = drive[3] # Write
stats.append(statele)


## Turns it off.
activeVM[0].setMemoryStatsPeriod(5, libvirt.VIR_DOMAIN_AFFECT_LIVE)

## Finished,  closing.
con.close()


#####################################################################
## Calculations in the following functions are taken from virtmanager
## https://github.com/virt-manager/virt-manager
## specific file: https://github.com/virt-manager/virt-manager/blob/main/virtManager/lib/statsmanager.py
def calcCPUPercent(currTimeStamp, prevTimeStamp, countCPU, currCPUTime, prevCPUTime):
    cpuTime = s['cpu_time'] - stats[i-1]['cpu_time']
    pcentbase = (
        ((cpuTime) * 100.0) /
        ((s['time_stamp'] - stats[i-1]['time_stamp']) * 1000.0 * 1000.0 * 1000.0))
    return countCPU > 0 and pcentbase / countCPU or 0

def calcRAMPercent(currTimeStamp, prevTimeStamp, ramActual, ramUnused):
    curmem = max(0, ramActual - ramUnused)
    currMemPercent = (curmem / float(ramActual)) * 100
    return max(0.0, min(currMemPercent, 100.0))

def calcRate(currTimeStamp, prevTimeStamp, currVal, prevVal):
    ratediff = currVal - prevVal
    timediff = currTimeStamp - prevTimeStamp
    ret = float(ratediff) / float(timediff)
    return max(ret, 0.0)

#####################################################################

fname = input("Name the output file (res.csv): ")
if fname == "":
    fname = "res.csv"

print("===Writing to file===")
f = open(f"results/{fname}", 'w')

# header
head = "Timestamp;CPU_Utilazation%;RAM_Utilization%;NetRx(KByte/s);NetTx(KByte/s);Read(KByte/s);Write(KByte/s)"
f.write(head)

for i in tqdm(range(1, len(stats))):
    s = stats[i]
    cpuGuestPercent = calcCPUPercent(s["time_stamp"], stats[i-1]["time_stamp"], 
            guestcpus, s["cpu_time"], stats[i-1]["cpu_time"])
    
    ramPercent = calcRAMPercent(s["time_stamp"], stats[i-1]["time_stamp"], s["ram_actual"], s["ram_unused"])

    netRxRate = calcRate(s["time_stamp"], stats[i-1]["time_stamp"], s["net.0.rx.bytes"], stats[i-1]["net.0.rx.bytes"])
    netTxRate = calcRate(s["time_stamp"], stats[i-1]["time_stamp"], s["net.0.rx.bytes"], stats[i-1]["net.0.rx.bytes"])

    driveRdRate = calcRate(s["time_stamp"], stats[i-1]["time_stamp"], s["block.0.rd.bytes"], stats[i-1]["block.0.rd.bytes"])
    driveWrRate = calcRate(s["time_stamp"], stats[i-1]["time_stamp"], s["block.0.wr.bytes"], stats[i-1]["block.0.wr.bytes"])
    tstamp = datetime.fromtimestamp(int(s['time_stamp']))
    toFile = f"\n{tstamp};{cpuGuestPercent};{ramPercent};{netRxRate/1024};{netTxRate/1024};{driveRdRate/1024};{driveWrRate/1024}"
    f.write(toFile)

    # print(f"{datetime.fromtimestamp(s['time_stamp'])}: {cpuGuestPercent:.2f}%, ram: {ramPercent:.2f}%")
    # print(f"Net: {netRxRate/1024:.2f}KB/s - {netTxRate/1024:.2f}KB/s")
    # print(f"Drive: {driveRdRate/1024:.2f}KB/s - {driveWrRate/1024:.2f}KB/s")


f.close()
exit(0)
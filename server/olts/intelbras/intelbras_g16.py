from datetime import datetime
import random
import traceback
from olts.emulador import Emulador, ExitClient
import re

ONUS = {
    'slot': {
        '0': {
            'pon': {
                '1': [],
                '2': [],
                '3': [],
                '4': [],
                '5': [],
                '6': [],
                '7': [],
                '8': [],
                '9': [],
                '10': [],
                '11': [],
                '12': [],
                '13': [],
                '14': [],
                '15': [],
                '16': [],
            }
        }
    }
}

unauth = 0
for i in range(1, 17):
    authed = 0
    for j in range(1, 5):
        auth = random.choice([False, True])
        if auth:
            authed += 1
        else:
            unauth += 1
        onu = {
            'id': f'TSMX-{2:0>2x}{random.randint(2570, 65535):0>4x}{1:0>2x}',
            'auth': auth,
            'onu': authed if auth else unauth,
            'type': random.choice(['110Gb', 'R1v2']),
            'name': 'VLAN-1000' if auth else ''
        }
        ONUS['slot']['0']['pon'][str(i)].append(onu)


class Break(Exception):
    pass


class Clear(Exception):
    pass

class Manager(Emulador):

    def __login__(self):
        self.login = self.request('Username(1-64 chars): ')
        self.password =self.request('Password(1-96 chars): ', secure=True)
        self.__enabled = False
        self.places = []
        self.__ignore = [
            'screen-rows per-page 0',
        ]

        self.send(self.__name)
        return True

    @property
    def onus(self):
        return ONUS

    @property
    def __name(self):
        place = f'({self.places[-1]})' if self.places else ''
        enabled = '#' if self.__enabled else '>'
        return f'OLT01-G16-[TSMX]{place}{enabled} '

    def __enable(self):
        if self.__enabled:
            self.send_error()
        else:
            self.__enabled = True

    def send_error(self, message="Comando não encontrado."):
        self.sendLine(message)

    def __config(self):
        if self.__enabled and not self.places:
            self.places.append('config')
        else:
            self.send_error()

    def __get_onu_pon(self, onus, auth=True):
        return filter(lambda onu: onu['auth'] == auth, onus)
    
    def __new_date(self):
        return datetime.now().strftime('%Y/%m/%d %H:%M:%S')


    def __ont_find(self, cmds):
        if not cmds or cmds[0] == '?':
            self.send_error('config  configuration information')
            self.send_error('list    list')
        if cmds[0] == 'list':
            if not len(cmds) > 1 or cmds[1] == '?':
                self.send_error('interface  interface')
                self.send_error('sn         ONT SN')
            else:
                if cmds[1] == 'interface':
                    if not len(cmds) > 2 or cmds[2] != 'gpon':
                        self.send_error('gpon    GPON')
                    else:
                        if not len(cmds) > 3 or not re.match(r'^((0\/(1[0-6]|[1-9]))|all)$', cmds[3]):
                            self.send_error(
                                'STRING<3-4>\tthe GPON port should be inputted with slot-num<0-0>/port-num<1-16>')
                            self.send_error('all\t\tall')
                        else:
                            lines = []

                            if cmds[3] == 'all':
                                index = 1
                                for p in self.onus['slot']['0']['pon']:
                                    for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][p], False):
                                        lines.append(
                                            f'g0/{p}\t{index}\t{onu["id"]}\t\t{self.__new_date()}\t\t3')
                                        index += 1
                            else:
                                pon = cmds[3].split('/')[-1]
                                index = 1
                                for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][pon], False):
                                    lines.append(
                                        f'g0/{pon}\t{index}\t{onu["id"]}\t\t{self.__new_date()}\t\t3')
                                    index += 1
                            if lines:
                                self.sendLine(
                                    'Port\tIndex\tSN\t\t\tLast-find\t\t\tFind-cnt‘')
                                for line in lines:
                                    self.sendLine(line)
                            self.sendLine(f'Total entries: {len(lines)}')

    def __optical_info(self, cmds):
        if not cmds or not re.match(r'^(0\/(1[0-6]|[1-9])\/(1[0-1][0-9]|12[0-8]|[0-9]{1,2}))$', cmds[0]):
            self.send_error(
                'STRING<5-8>\tthe ONU port should be inputted with slot-num<0-0>/port-num<1-16>/ont-num<1-128>')
            return
        
        slot, pon, ont = cmds[0].split('/')

        for onu in self.onus['slot'][slot]['pon'][pon]:
            if onu['onu'] == int(ont) and onu['auth']:
                info = f'''Power Feed Voltage(V):   {random.randint(2, 4)}.{random.randint(0, 99):02d}
RX Optical Power(dBm): -{random.randint(20, 30)}.{random.randint(0, 999):03d}  (OLT TX: {random.randint(2, 3)}.{random.randint(0, 999):03d})
TX Optical Power(dBm):   {random.randint(2, 3)}.{random.randint(0, 999):03d}    (OLT RX: -{random.randint(20, 30)}.{random.randint(0, 999):03d})
Laser Bias Current(mA):   {random.randint(12, 17)}.{random.randint(0, 999):03d}
Temperature(C):   {random.randint(40, 60)}.{random.randint(0, 99):02d}
CATV RX Power(dBm): -
CATV Output Power(dBmV): -
'''
                self.sendLine(info)
                return
        self.send_error('ONT not found')

    def __ont(self, cmds):
        '''show ont brief interface gpon'''
        if not len(cmds) > 1 or cmds[1] not in ['brief', 'optical-info']:
            self.send_error('brief         brief')
            self.send_error('optical-info  optical-info')
        else:
            if cmds[1] == 'optical-info':
                return self.__optical_info(cmds[2:])
            if not len(cmds) > 2 or cmds[2] not in ['interface', 'sn']:
                self.send_error('interface    interface')
                self.send_error('sn           sn')
            else:
                if cmds[2] == 'interface':
                    if not len(cmds) > 3 or cmds[3] != 'gpon':
                        self.send_error('gpon    GPON')
                    else:
                        if not len(cmds) > 4 or not re.match(r'^((0\/(1[0-6]|[1-9]))|all)$', cmds[4]):
                            self.send_error(
                                'STRING<3-4>\tthe GPON port should be inputted with slot-num<0-0>/port-num<1-16>')
                            self.send_error('all\t\tall')
                        else:
                            lines = []

                            if cmds[4] == 'all':
                                for p in self.onus['slot']['0']['pon']:
                                    for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][p], True):
                                        lines.append(
                                            f'0/{p}/{onu["onu"]}\t{onu["id"]}\t\t{onu["type"]}\t\t0d0h0m\t\tonline\tworking')
                            else:
                                pon = cmds[4].split('/')[-1]
                                for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][pon], True):
                                    lines.append(
                                        f'0/{pon}/{onu["onu"]}\t{onu["id"]}\t\t{onu["type"]}\t\t0d0h0m\t\tonline\tworking')
                            if lines:
                                self.sendLine(
                                    'ONT\tSN\t\t\tDevice-type\tUp/Down-time\tStatus\tW/S')
                                for line in lines:
                                    self.sendLine(line)
                            self.sendLine(f'Total entries: {len(lines)}')
                else:
                    if not len(cmds) > 3 or cmds[3] != 'string-hex':
                        self.send_error('string-hex    string-hex')
                    else:
                        if not len(cmds) == 5 or not re.match(r'^TSMX-([0-9a-fA-F]){8}$', cmds[4]):
                            self.send_error(
                                'STRING<13>\tthe sn should be inputted with XXXX-xxxxxxxx')
                        else:
                            lines = []
                            for pon in self.onus['slot']['0']['pon']:
                                for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][pon], True):
                                    if onu['id'] == cmds[4]:
                                        lines.append(
                                            f'0/{pon}/{onu["onu"]}\t{onu["id"]}\t\t{onu["type"]}\t\t0d0h0m\t\tonline\tworking'
                                        )
                            if lines:   
                                self.sendLine(
                                    'ONT\tSN\t\t\tDevice-type\tUp/Down-time\tStatus\tW/S')
                                for line in lines:
                                        self.sendLine(line)
                            self.sendLine(f'Total entries: {len(lines)}')   


    def __deploy(self, cmds):
        '''show deploy rule brief interface gpon'''
        if not cmds or cmds[0] == '?':
            self.send_error('rule  rule information')
        if cmds[0] == 'rule':
            if not len(cmds) > 1 or cmds[1] != 'brief':
                self.send_error('brief  brief')
            else:
                if not len(cmds) > 2 or cmds[2] != 'interface':
                    self.send_error('interface    interface')
                else:
                    if not len(cmds) > 3 or cmds[3] != 'gpon':
                        self.send_error('gpon    GPON')
                    else:
                        if not len(cmds) > 4 or not re.match(r'^((0\/(1[0-6]|[1-9]))|all)$', cmds[4]):
                            self.send_error(
                                'STRING<3-4>\tthe GPON port should be inputted with slot-num<0-0>/port-num<1-16>')
                            self.send_error('all\t\tall')
                        else:
                            lines = []

                            if cmds[4] == 'all':
                                for p in self.onus['slot']['0']['pon']:
                                    for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][p], True):
                                        lines.append(
                                            f'0/{p}/{onu["onu"]}\t{random.choice(["Inused", "Unused"])}\tSN\t\t{onu["id"]}')
                            else:
                                pon = cmds[4].split('/')[-1]
                                for onu in self.__get_onu_pon(self.onus['slot']['0']['pon'][pon], True):
                                    lines.append(
                                        f'0/{pon}/{onu["onu"]}\t{random.choice(["Inused", "Unused"])}\tSN\t\t{onu["id"]}')
                            if lines:
                                self.sendLine(
                                    'ONT\tStatus\tAuth-mode\tAuth-info')
                                for line in lines:
                                    self.sendLine(line)
                            self.sendLine(f'Total entries: {len(lines)}')

    def show(self, cmd):
        if not self.__enabled:
            raise Exception('Comando não encontrado.')
        cmds = cmd.split()[1:]

        if cmds[0] == 'ont-find':
            self.__ont_find(cmds[1:])
        elif cmds[0] == 'deploy':
            self.__deploy(cmds[1:])
        elif cmds[0] == 'ont':
            self.__ont(cmds)
        else:
            raise Exception('Comando não encontrado.')
        

    def __deploy_profile_rule(self):
        try:
            def handle(data, aimmed, aimmedonu, set_aimmed, set_aimmedonu):
                if isinstance(data, bytes):
                    data = data.decode()
                data = data.strip()
                if data == 'exit':
                    if self.places and self.places[-1] == 'deploy-profile-rule':
                        self.places.pop()
                        raise Break()
                    elif not self.places[-1].startswith('deploy-profile-rule'):
                        raise Break()
                    else:
                        self.places.pop()
                        raise Clear()
                args = data.split()
                if args[0] == 'show':
                    self.show(data)
                elif not aimmed and args[0] == 'delete' and args[1] == 'aim' and re.match(r'^(0\/(1[0-6]|[1-9])\/(1[0-1][0-9]|12[0-8]|[0-9]{1,2}))$', args[2]):
                    slot, pon, ont = args[2].split('/')
                    found = False
                    for onu in ONUS['slot'][slot]['pon'][pon]:
                        if onu['onu'] == int(ont) and onu['auth']:
                            confirm = self.request("Are you sure to delete the ONT {}? ".format(onu['id']))
                            if isinstance(confirm, bytes):
                                confirm = confirm.decode()
                            confirm = confirm.strip()
                            if confirm and confirm == 'y':
                                onu['auth'] = False
                                self.sendLine(f'ONT {args[2]} deleted')
                            found = True
                            break
                    if not found:
                        self.send_error(f'ONT not found')
                            
                elif args[0] == 'aim' and re.match(r'^(0\/(1[0-6]|[1-9])\/(1[0-1][0-9]|12[0-8]|[0-9]{1,2}))$', args[1]):
                    set_aimmed(args[1].split('/'))                    
                    self.places.append(f"deploy-profile-rule-{'-'.join(aimmed)}")
                elif aimmed and (aimmedonu and data == 'active'):
                    slot, pon, ont = aimmed
                    try:
                        list(filter(lambda x: x['auth'] and x['onu'] == int(
                            ont), ONUS['slot'][slot]['pon'][pon]))[0]
                        self.send_error(f'ONU already activated')
                    except:
                        found = False
                        for onu in ONUS['slot'][slot]['pon'][pon]:
                            if onu['id'] == aimmedonu and not onu['auth']:
                                onu['onu'] = int(ont)
                                onu['auth'] = True
                                self.sendLine(f'ONT {aimmed} activated')
                                found = True
                                break
                        if not found:
                            self.send_error(f'ONT not found')
                elif aimmed and re.match(r'^permit sn string-hex TSMX-([0-9a-fA-F]){8} line \d+ default line \d+$', ' '.join(args)):
                    slot,pon,onu = aimmed
                    serial = data.strip().split()[3]
                    try:
                        _onu = list(filter(lambda x: x['auth'] and (x['onu'] == int(
                            onu) or x['id'] == serial), ONUS['slot'][slot]['pon'][pon]))[0]
                        if _onu['id'] == serial:
                            self.send_error(f'ONU already activated')
                        self.send_error(f'Index already used')
                    except:
                        set_aimmedonu(serial)
                else:
                    print(aimmed, aimmedonu)
                    if args:
                        self.send_error(f'Comando não encontrado: {data}')

            data = self.request(self.__name)
            aimmed = []
            aimmedonu = None

            def set_aimmed(val):
                global aimmed
                aimmed = val

            def set_aimmedonu(val):
                global aimmedonu
                aimmedonu = val

            while self.running:
                do_exit = False
                for d in re.split(r'\r?\n|\n|\r', data.strip()):
                    try:
                        handle(d, aimmed, aimmedonu, set_aimmed, set_aimmedonu)
                    except Break:
                        do_exit = True
                        break
                    except Clear as e:
                        aimmed = []
                        aimmedonu = None
                    except Exception as e:
                        traceback.print_exc()
                        self.send_error(str(e))
                if do_exit:
                    break
                else:
                    data = self.request(self.__name)

        except Exception as e:
            traceback.print_exc()
            self.send_error(str(e))
        finally:
            self.places.pop()
        
        

    def deploy(self, cmd):
        if self.places and self.places[0] == 'config':
            cmds = cmd.split()[1:]
            if cmds and cmds[0] == 'profile':
                if len(cmds) == 2 and cmds[1] == 'rule':
                    self.places.append('deploy-profile-rule')
                    return self.__deploy_profile_rule()
        raise Exception('Comando não encontrado.')
        


    def receive(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        data = (data or '').strip()

        try:
            if data == 'exit':
                if self.places:
                    self.places.pop()
                elif self.__enabled:
                    self.__enabled = False
                else:
                    raise ExitClient()
            elif data == 'enable':
                self.__enable()
            elif data == 'configure terminal':
                self.__config()
            elif data.startswith('show '):
                return self.show(data)
            elif data.startswith('deploy '):
                return self.deploy(data)
            elif data in self.__ignore:
                pass
            else:   
                if data.strip():
                    self.send_error("Comando não encontrado: %s" % data)
        except ExitClient as e:
            raise e
        except Exception as e:
            traceback.print_exc()
            self.send_error(str(e))
        finally:
            self.send(self.__name)


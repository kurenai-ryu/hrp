----------------------------------------
-- script-name: clou_dissector.lua
--
-- author: Arturo Hernandez
-- Copyright (c) 2018
-- This code is in the Public Domain, or the BSD (3 clause) license if Public Domain does not apply
-- in your country.
--
-- Version: 1.0
--
-- colorize rule
--
-- (clou) && (tcp.dstport==9090)
--
----------------------------------------
print("hello world2")
-- do not modify this table
local debug_level = {
    DISABLED = 0,
    LEVEL_1  = 1,
    LEVEL_2  = 2
}

PASIVE = 0
ACTIVE = 1

OUT = 0
IN = 1

-- set this DEBUG to debug_level.LEVEL_1 to enable printing debug_level info
-- set it to debug_level.LEVEL_2 to enable really verbose printing
-- note: this will be overridden by user's preference settings
local DEBUG = debug_level.LEVEL_1

local default_settings = {
    debug_level  = DEBUG,
    port         = 9090,
    heur_enabled = false,
}

local dprint = function() end
local dprint2 = function() end
local function reset_debug_level()
    if default_settings.debug_level > debug_level.DISABLED then
        dprint = function(...)
            print(table.concat({"Lua:", ...}," "))
        end

        if default_settings.debug_level > debug_level.LEVEL_1 then
            dprint2 = dprint
        end
    end
end
-- call it now
reset_debug_level()

dprint2("Wireshark version = ", get_version())
dprint2("Lua version = ", _VERSION)

----------------------------------------
-- Unfortunately, the older Wireshark/Tshark versions have bugs, and part of the point
-- of this script is to test those bugs are now fixed.  So we need to check the version
-- end error out if it's too old.
local major, minor, micro = get_version():match("(%d+)%.(%d+)%.(%d+)")
if major and tonumber(major) <= 1 and ((tonumber(minor) <= 10) or (tonumber(minor) == 11 and tonumber(micro) < 3)) then
        error(  "Sorry, but your Wireshark/Tshark version ("..get_version()..") is too old for this script!\n"..
                "This script needs Wireshark/Tshark version 1.11.3 or higher.\n" )
end

-- more sanity checking
-- verify we have the ProtoExpert class in wireshark, as that's the newest thing this file uses
assert(ProtoExpert.new, "Wireshark does not have the ProtoExpert class, so it's too old - get the latest 1.11.3 or higher")

----------------------------------------
-- creates a Proto object, but doesn't register it yet
local clou_udp = Proto("clou_udp","Clou UDP Protocol")
local clou = Proto("clou","Clou/Hopeland HRP Protocol")

local tcp_port_f = Field.new("tcp.dstport")

-- from CLreader-api.h
local eBAUD = {
    [0] = "B_9600",
    [1] = "B_19200",
    [2] = "B_115200"
}

local eANT = {
    [1] = "ANT_1",
    [2] = "ANT_2",
    [4] = "ANT_3",
    [8] = "ANT_4",
    [16] = "ANT_5",
    [32] = "ANT_6",
    [64] = "ANT_7",
    [128] = "ANT_8"
}

local eREAD_TYPE = {
    [0] = "SINGLE",
    [1] = "INVENTORY"
}

local eRF_REGION = {
    [0] = "GB1  920~925MHz",
    [1] = "GB2  840~845MHz",
    [2] = "GB3  840~845MHz & 920~925MHz",
    [3] = "FCC  902~928MHz",
    [4] = "ETSI 866~868MHz",
    [5] = "JP   916.8~920.4MHz",
    [6] = "TW   922.25~927.75MHz",
    [7] = "INA  923.125~925.125MHz",
    [8] = "RUS  866.6~867.4MHz"
}


local eFREQ_JMP = {
    [0] = "SEQUEN_SWITCH",
    [1] = "AUTO_SWITCH" --test if its correct (official is 0 too)
}

local tGPIO_LEVEL = {
    [0] = "Low Level",
	[1] = "High Level"
}

local tFrameHead = {
    [0xAA] = "Frame HEAD"
}

local tRS485Flag = {
    [0]="no RS485",
    [1] = "message RS485"
}

local tActiveFlag = {
    [0]="from Computer (or response)",
    [1] = "from Reader"
}

local tMessageType = {
    [0]="Reader Error or Warning",
    [1] = "Reader Configuration and management",
    [2] = "RFID Configuration and operation",
    [3] = "Reader log",
    [4] = "Reader application",
    [5] = "Testing command"
}
local tMessagesIds = {
  [1]={
    [0x00] = "Query reader information",
    [0x01] = "Query baseband software version",
    [0x02] = "Configure RS232 parameter",
    [0x03] = "Query RS232 parameter",
    [0x04] = "Configure reader IP",
    [0x05] = "Query reader IP",
    [0x06] = "Query reader MAC",
    [0x07] = "Configure server/client mode parameter",
    [0x08] = "Query server/client mode parameter",
    [0x09] = "Configure GPO status",
    [0x0A] = "Query GPI status",
    [0x0B] = "Configure GPI trigger parameter",
    [0x0C] = "Query GPI trigger parameter",
    [0x0D] = "Configure wiegand communication parameter",
    [0x0E] = "Query wiegand communication parameter",
    [0x0F] = "Re-start reader",
    [0x10] = "Configure reader system time",
    [0x11] = "Query reader system time",
    [0x12] = "Connection status confirmation",
    [0x13] = "Configure reader MAC",
    [0x14] = "Restore reader default configuration",
    [0x15] = "Configure reader RS485 device address",
    [0x16] = "Query reader RS485 device address",
	[0x1B] = "Get cached data...",
  },
  [2]={
    [0x00] = "Query reader RFID ability",
    [0x01] = "Configure reader power",
    [0x02] = "Query reader power",
    [0x03] = "Configure reader RF frequency band",
    [0x04] = "Query reader RF frequency band",
    [0x05] = "Configure reader working frequency",
    [0x06] = "Query reader working frequency",
    [0x07] = "Configure reader antenna",
    [0x08] = "Query reader antenna",
    [0x09] = "Configure tag upload parameters",
    [0x0A] = "Query tag upload parameters",
    [0x0B] = "Configure EPC baseband parameters",
    [0x0C] = "Query EPC baseband parameters",
    [0x0D] = "Configure reader auto-idle mode",
    [0x0E] = "Query reader auto-idle mode",
    [0x0F] = "Reserved NA",
    [0x10] = "Read EPC tag",
    [0x11] = "Write EPC tag",
    [0x12] = "Lock tag",
    [0x13] = "Kill tag",
    [0x40] = "read 6B tag",
    [0x41] = "Write 6B tag",
    [0x42] = "Lock 6B tag",
    [0x43] = "Query 6B tag locking",
    [0xFF] = "Stop command",
  },
  [4]={
    [0x00] = "Device application software upgrade",
    [0x01] = "Baseband software upgrade",
  },
  [5]={
    [0x00] = "Transmitting carrier command",
    [0x05] = "Antenna port SWR detection",
  },
}

local pf_fh = ProtoField.new ("Frame Head", "clou.fh", ftypes.UINT8, tFrameHead)
local pf_rs485f = ProtoField.new ("RS485 Flag", "clou.rs485f", ftypes.UINT8, tRS485Flag,nil, 0x20)
local pf_af = ProtoField.new ("Active Flag", "clou.af", ftypes.UINT8, tActiveFlag, nil, 0x10)
local pf_mt = ProtoField.new ("Message Type", "clou.mt", ftypes.UINT8, tMessageType,nil, 0x0F)
local pf_mid = ProtoField.new ("Message ID", "clou.mid", ftypes.UINT8, nil, base.HEX)
local pf_mid_1 = ProtoField.new ("Message ID", "clou.mid", ftypes.UINT8, tMessagesIds[1], base.HEX)
local pf_mid_2 = ProtoField.new ("Message ID", "clou.mid", ftypes.UINT8, tMessagesIds[2], base.HEX)
local pf_mid_4 = ProtoField.new ("Message ID", "clou.mid", ftypes.UINT8, tMessagesIds[4], base.HEX)
local pf_mid_5 = ProtoField.new ("Message ID", "clou.mid", ftypes.UINT8, tMessagesIds[5], base.HEX)
local pf_sadr = ProtoField.new ("Serial address", "clou.sadr", ftypes.UINT8, nil, base.HEX)
local pf_dlength  = ProtoField.new ("Data length", "clou.dlength", ftypes.UINT16)
local pf_data     = ProtoField.new ("Data", "clou.data", ftypes.BYTES, nil, base.DOT)
local pf_checksum = ProtoField.new ("Checksum", "clou.checksum", ftypes.UINT16, nil, base.HEX)
local pf_string   = ProtoField.new ("Data", "clou.string", ftypes.STRING)

clou.fields = {
  pf_fh,
  pf_rs485f, pf_af, pf_mt,
  pf_mid, pf_mid_1, pf_mid_2, pf_mid_4, pf_mid_5, pf_string,
  pf_sadr,
  pf_dlength, pf_data,
  pf_checksum
}


local ef_too_short = ProtoExpert.new("clou.too_short.expert", "Clou message too short",
                                     expert.group.MALFORMED, expert.severity.ERROR)
clou.experts = {ef_too_short}

function gen_none()
  return {0, function(dt, tb, ptr)
    dt:add(pf_string, tb:range(ptr,0),"", "-")
    return ptr
  end}
end

function gen_strX(pid, name, size)
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tostring(tb:range(ptr, size):bytes())
    dt:add(pf_string, tb:range(ptr - inco , size + inco),
      val, string.format("%s -> %s", name, val))
    return ptr + size
  end}
end

function gen_uintX(pid, name, size)
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tb:range(ptr, size):uint()
    dt:add(pf_string, tb:range(ptr - inco , size + inco),
      val, string.format("%s = 0x%0"..(size*2).."X", name, val))
    return ptr + size
  end}
end

function gen_uint(pid, name, size)
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tb:range(ptr, size):uint()
    dt:add(pf_string, tb:range(ptr - inco, size + inco),
      val, string.format("%s = %u", name, val))
    return ptr + size
  end}
end

function gen_flt(pid, name, factor, size)
  factor = factor or 1.0
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tb:range(ptr, size):uint()
    dt:add(pf_string, tb:range(ptr - inco, size + inco),
      val, string.format("%s = %.2f", name, (val * factor)))
    return ptr + size
  end}
end

function gen_table(pid, name, table, size)
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tb:range(ptr, size):uint()
    if table[val] ~= nil then val = table[val] end
    dt:add(pf_string, tb:range(ptr - inco, size + inco),
      val, name .. " = " .. val)
      return ptr + size
  end}
end

function gen_bitmask(pid, name, table, size)
  size = size or 1
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local val = tb:range(ptr, size):uint()
    local con = "" -- TODO complete!
    if table[val] ~= nil then val = table[val] end
    dt:add(pf_string, tb:range(ptr - inco, size + inco),
      val, name .. " = " .. val)
      return ptr + size
  end}
end
function gen_var_string(pid, name)
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local size = tb:range(ptr,2):uint()
    local val = (tb:range(ptr + 2, size):string())
    dt:add(pf_string, tb:range(ptr - inco, inco + 2 + size),
      val, string.format("%s[%i] -> %s",name, size, val))
    return ptr + 2 + size
  end}
end


function gen_var2(pid, name)
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local size = tb:range(ptr,2):uint()
    local val = tostring(tb:range(ptr + 2, size):bytes())
    dt:add(pf_string, tb:range(ptr - inco, inco + 2 + size),
      val, string.format("%s[%i] -> %s",name, size, val))
    return ptr + 2 + size
  end}
end

function gen_var_table(pid, name, table) -- should be one byte
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local leng = tb:range(ptr, 2):uint()
    dt:add(pf_string, tb:range(ptr - inco, 2 + inco),
      "", name .. " list size " .. leng)
    local val
    for i = 1, leng do
      val = tb:range(ptr + 1 + i, 1):uint() --fixed size 1
      if table[val] ~= nil then
        val = table[val]
      else
        val = "##" .. tostring(val)
      end
      dt:add(pf_string, tb:range(ptr + 1 + i, 1),
        val,"\t" .. name .. " = " .. val)
    end
    return ptr + 2 + leng
  end}
end
--read parameter
function gen_var_read(pid, name)
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local tsize = tb:range(ptr, 2):uint()
    local tarea = {[0] = "Data Area", [1]= "EPC", [2]="TID", [3]="user"}
    local area = tb:range(ptr + 2, 1):uint()
    local start= tb:range(ptr + 3, 2):uint()
    local size = tb:range(ptr + 5, 1):uint() -- in bits! not bytes nor words
    local val = tostring(tb:range(ptr + 6, tsize-4):bytes())
    dt:add(pf_string, tb:range(ptr - inco, inco + 2 + tsize),
      val, string.format("%s:%s:[%i][%s] -> %s",name, tarea[area], start, size, val))
    return ptr + 2 + tsize
  end}
end

function gen_adr_read(pid, name)
  local inco = 0
  if pid > 0 then inco = 1 end
  return {pid, function(dt, tb, ptr)
    local size = 3 -- fixed
    local start= tb:range(ptr, 2):uint()
    local val = tb:range(ptr + 2, 1):uint()
    dt:add(pf_string, tb:range(ptr - inco, inco + size),
      val, string.format("%s = [%u][%u]",name, start, val))
    return ptr + size
  end}
end

local tParams = {
  [PASIVE] = {
    [OUT] = { -- from PC to reader
	    [0x01] = {
	      [0x0C] = {
		      gen_table(0, "GPI port", {[0]="GPI1",[1]="GPI2",[2]="GPI3",[3]="GPI4"})
		    }
	    },
      [0x02] = {
	    [0x03] = { -- configure band
		  gen_table(0, "Frecuency Band", eRF_REGION),
		},
		[0x05] = {
		  gen_table(0, "Freq. auto setting", {[0]="from channel list", [1]="auto band (ignore list)"}),
		  gen_var_table(1,"Channel list",{})
		},
        [0x0b] = {
          gen_table(1, "EPC baseband speed",{
            [0]="Tari=25us, FM0, LHF=40khz",
            [1]="Tari=25us, Miller4, LHF=250khz",
            [2]="Tari=25us, Miller4, LHF=300khz",
            [3]="Tari=6.25us, FM0, LHF=400khz",
            [255] = "Auto"}),
          gen_uint (2, "Default Q Value"),
          gen_uint (3, "Session"),
          gen_table(4, "Inventory flag",{
            [0]="use flag A",
            [1]="use flag B",
            [2]="Use both A & B"})
        },
        [0x10] = {
          gen_bitmask (0, "Antenna", eANT),
          gen_table   (0, "Inv/Sing Read Type", {[0]="Single Read", [1]="Continous"}),
          gen_var_read(1, "MatchParameter"),
          gen_uintX   (2, "Tid read", 2),
          gen_adr_read(3, "UserData read"),
          gen_adr_read(4, "ReservedData read"),
          gen_uintX   (5, "Access password", 4),
          gen_table   (6, "MONZA QT", {[1]="Read"}),
          gen_table   (7, "RFMICRON temp", {[1]="Read"}),
          gen_table   (8, "EM Sensor Data", {[1]="Read"}),
          gen_adr_read(9, "EPC data"),
        },
        [0x11] = { --write tag
          gen_bitmask (0, "antenna port", eANT),
          gen_table   (0, "Data Area", {[0]="Reserverd", [1]="EPC", [2]="TID", [3]="user"}),
          gen_uintX   (0, "start address",2),
          gen_var2    (0, "Data content"),
          gen_var_read(1, "MatchParameter"),
          gen_uintX   (2, "access password", 4),
          gen_uint    (3, "block write")
        },
        [0xFF] = {gen_none()},
      },
    },
    [IN] = { -- reader response
	  [0x01]={ --config management
	    [0x00]={ --quiery reader info
		  gen_uintX(0,"App software version",4), -- TODO: parse version "u16.u8.u8"
		  gen_var_string(0, "Reader Name"),
		  gen_uint(0,"Power-on time [s]", 4)
	    },
		[0x01]={
		  gen_uintX(0,"BaseBand software version",4), -- TODO: parse version "u16.u8.u8"
		},
		[0x08] = { --server/client mode
		  gen_table(0,"Mode",{[0]="Server",[1]="Client"}),
		  gen_uint (0, "server TCP port", 2),
		  gen_uintX(0, "client IP addr", 4), -- TODO: replace with gen_ip
		  gen_uint (0, "client TCP port", 2),
		},
		[0x0A]={
		  gen_table(1,"GPI1 Level", tGPIO_LEVEL),
		  gen_table(2,"GPI2 Level", tGPIO_LEVEL),
		  gen_table(3,"GPI3 Level", tGPIO_LEVEL),
		  gen_table(4,"GPI4 Level", tGPIO_LEVEL),
		},
		[0x0C] = {
		  gen_table(0, "Trigger start condition", {[0]="OFF", [1]="Low level", [2]="high level", [3]="rising edge", [4]="falling edge", [5]="random edge"}),
		  gen_var2(0, "trigger command"),
		  gen_table(0, "Trigger stop condition", {[0]="NO stop", [1]="Low level", [2]="high level", [3]="rising edge", [4]="falling edge", [5]="random edge", [6]="delaystop"}),
		  gen_uint (0,"Delay Stop Time [x10ms]", 2),
		  gen_table(0, "reset trigger", {[0]="don't update", [1]="update"})

		},
		[0x01b]={
		  gen_table(0,"Get Cached data", {[0]="cache exists", [1]="no cache", [2]="upload end"}),
		}
	  },
      [0x02] = { --0x02 reader cuality
        [0x00] = {
          gen_uint ( 0,"Min.RF out power (db)"),
          gen_uint ( 0, "Max.RF out power(db)"),
          gen_uint ( 0, "Antenna Qty"),
          gen_var_table( 0, "Supported Frequency", eRF_REGION),
          gen_var_table( 0, "RFID Protocol",{
            [0]="ISO18000-6C/EPC C1G2",
            [1]="ISO18000-6B",
            [2]="China standard GB/T 29768-2013",
            [3]="China Military GB/T 7383.1-2011",
          }),
        },
        [0x01] = { --finnish
          gen_table( 0, "configure result",{
            [0]="single finished",
            [1]="incorrect port",
            [2]="unsupported power",
			[3]="save failed"}),
        },
		[0x03] = {
			gen_table(0, "Config result", {[0]="successful",[1]="reader doesn't support",[2]="save failed"})
		},
		[0x04] = {
			gen_table( 0, "RF Frequency Band", eRF_REGION),
		},
		[0x05] = {
			gen_table(0, "Config result", {[0]="successful",[1]="signal channel not in current frecuency band",[2]="Invalid Frecuency point Qty", [3]="other parameter error", [4]="save error"}),
		},
		[0x06] = {
			gen_table(0, "Freq. auto setting", {[0]="from channel list", [1]="auto band (ignore list)"}),
			gen_var_table(0,"Frequency Channel", {}),
		},
		[0x0a] = {
			gen_uint(0, "Repeat Tag Filtering Time (ms)", 2),
			gen_uint(0, "RSSI threshold")
		},
        [0x0b] = {
          gen_table( 0, "Config Result",{
            [0] = "Configure successfully",
            [1] = "Baseband speed reader don’t support.",
            [2] = "Q value parameter error",
            [3] = "Session parameter error",
            [4] = "Inventory parameter error",
            [5] = "Other parameter error",
            [6] = "Save failed"}),
        },
		[0x0e] = {
			gen_table(0, "Auto-idle mode", {[0]="disabled (close)", [1]="Enable auto idle"}),
			gen_uint(0,"Auto idle time (x10ms)",2)
		},
        [0x10] = {
          gen_table( 0, "Config Result",{
            [0] = "Configure successfully",
            [1] = "Antenna port parameter error",
            [2] = "Select read parameter error",
            [3] = "TID read parameter error",
            [4] = "UserData read parameter error",
            [5] = "Reserved area parameter error",
            [6] = "other param error"}),
        },
		[0x11] = {
		  gen_table(0, "Write result", {
		    [0] = "Write successful",
			[1] = "antenna port error",
			[2] = "select param error",
			[3] = "write param error",
			[4] = "CRC calib error",
			[5] = "power insufficient",
			[6] = "data area overflow",
			[7] = "data area locked",
			[8] = "access password error",
			[9] = "other tag error",
			[10] = "tag lost",
			[11] = "reader tx cmd error",
		  }),
		  gen_uint(1, "write failure word address", 2),
		},
		[0xff] = { --stop
          gen_table( 0, "Stop Result",{
            [0] = "Stop successful",
            [1] = "System Error",}),
        },
      },
    },
  },
  [ACTIVE] = {
    [IN] = {
      [0x02] = { -- 0x12
        [0x00] = { -- read tag!!!
          gen_var2 ( 0,"EPC"),
          gen_uintX( 0, "Tag PC Value", 2),
          gen_uint ( 0, "Antenna ID"),
          gen_uint ( 1, "RSSI"),
          gen_table( 2, "Result",{
            [0]="Successful",
            [1]="No response",
            [2]="CRC error",
            [3]="Data area locked",
            [4] ="Data area overflow",
            [5]="Access password error",
            [6]="Other tag error",
            [7]="Other reader error"
          }),
          gen_var2 ( 3, "TID"),
          gen_var2 ( 4, "UserData"),
          gen_var2 ( 5, "ReservedData"),
          gen_uint ( 6, "Sub antenna"),
          { 7, function(dt, tvbuf, ptr)
            local size = 8
            local val1 = tvbuf:range(ptr, 4):uint()
            local val2 = tvbuf:range(ptr + 4 , 4):uint()
            dt:add(pf_string, tvbuf:range(ptr-1, size+1),
              val, string.format("UTC =  %i.%06i ms", val1, val2))
            ptr = ptr + size
            return ptr
          end},
          gen_uintX( 8, "Sequence No", 4),
          gen_uint ( 9, "Freq[kHz]", 4),
          gen_flt  (10, "Phase[°]", 0.0490625),
          gen_strX (11, "EM sensor data", 8),
          gen_var2 (12, "EPC Data"),
        },
		[0x01] = { --reader finish
			gen_table( 0, "Tag Finnish Reason",{
				[0] = "Single Operation finished",
				[1] = "Received stop command",
				[2] = "hardware abnormal interrupt"}),
		},
      },
    }
  }
}


-- here's a little helper function to access the response_field value later.
-- Like any Field retrieval, you can't retrieve a field's value until its value has been
-- set, which won't happen until we actually use our ProtoFields in TreeItem:add() calls.
-- So this isResponse() function can't be used until after the pf_flag_response ProtoField
-- has been used inside the dissector.
-- Note that calling the Field object returns a FieldInfo object, and calling that
-- returns the value of the field - in this case a boolean true/false, since we set the
-- "mydns.flags.response" ProtoField to ftype.BOOLEAN way earlier when we created the
-- pf_flag_response ProtoField.  Clear as mud?
--
-- A shorter version of this function would be:
-- local function isResponse() return response_field()() end
-- but I though the below is easier to understand.
local function isResponse()
    local response_fieldinfo = response_field()
    return response_fieldinfo()
end

--------------------------------------------------------------------------------
-- preferences handling stuff
--------------------------------------------------------------------------------

-- a "enum" table for our enum pref, as required by Pref.enum()
-- having the "index" number makes ZERO sense, and is completely illogical
-- but it's what the code has expected it to be for a long time. Ugh.
local debug_pref_enum = {
    { 1,  "Disabled", debug_level.DISABLED },
    { 2,  "Level 1",  debug_level.LEVEL_1  },
    { 3,  "Level 2",  debug_level.LEVEL_2  },
}

clou.prefs.debug = Pref.enum("Debug", default_settings.debug_level,
                            "The debug printing level", debug_pref_enum)

clou.prefs.port  = Pref.uint("Port number", default_settings.port,
                            "The UDP port number for MyDNS")

clou.prefs.heur  = Pref.bool("Heuristic enabled", default_settings.heur_enabled,
                            "Whether heuristic dissection is enabled or not")

----------------------------------------
-- a function for handling prefs being changed
function clou.prefs_changed()
    dprint2("prefs_changed called")

    default_settings.debug_level  = clou.prefs.debug
    reset_debug_level()

    default_settings.heur_enabled = clou.prefs.heur

    if default_settings.port ~= clou.prefs.port then
        -- remove old one, if not 0
        if default_settings.port ~= 0 then
            dprint2("removing CLOU from port",default_settings.port)
            DissectorTable.get("tcp.port"):remove(default_settings.port, clou)
        end
        -- set our new default
        default_settings.port = dns.prefs.port
        -- add new one, if not 0
        if default_settings.port ~= 0 then
            dprint2("adding clou to port",default_settings.port)
            DissectorTable.get("tcp.port"):add(default_settings.port, clou)
        end
    end
end
dprint2("CLOU Prefs registered")

----------------------------------------
---- some constants for later use ----
local ZK_PACKET_LEN = 7

function data_tree_diss(data_tree, params, tvbuf,ptr,size,ptr2,size2)
  local val
  if size > 4 then
    val = tostring(tvbuf:range(ptr, size):bytes())
  else
    val = tvbuf:range(ptr, size):uint()
  end
end


----------------------------------------
-- The following creates the callback function for the dissector.
-- It's the same as doing "dns.dissector = function (tvbuf,pkt,root)"
-- The 'tvbuf' is a Tvb object, 'pktinfo' is a Pinfo object, and 'root' is a TreeItem object.
-- Whenever Wireshark dissects a packet that our Proto is hooked into, it will call
-- this function and pass it these arguments for the packet it's dissecting.

function clou.dissector(tvbuf, pktinfo, root)
    dprint2("clou.dissector called")
    -- set the protocol column to show our protocol name
    pktinfo.cols.protocol:set("HRP")
    local in_or_out
    if tostring(tcp_port_f()) == tostring(default_settings.port) then
      in_or_out = OUT
      pktinfo.cols.info = "-> "
    else
      in_or_out = IN
      pktinfo.cols.info = "<- "
    end

    -- We want to check that the packet size is rational during dissection, so let's get the length of the
    -- packet buffer (Tvb).
    -- Because DNS has no additional payload data other than itself, and it rides on UDP without padding,
    -- we can use tvb:len() or tvb:reported_len() here; but I prefer tvb:reported_length_remaining() as it's safer.
    local pktlen = tvbuf:reported_length_remaining()

    -- We start by adding our protocol to the dissection display tree.
    -- A call to tree:add() returns the child created, so we can add more "under" it using that return value.
    -- The second argument is how much of the buffer/packet this added tree item covers/represents - in this
    -- case (DNS protocol) that's the remainder of the packet.
    local tree = root:add(clou, tvbuf:range(0,pktlen))

    -- now let's check it's not too short
    if pktlen < ZK_PACKET_LEN then
        -- since we're going to add this protocol to a specific UDP port, we're going to
        -- assume packets in this port are our protocol, so the packet being too short is an error
        -- the old way: tree:add_expert_info(PI_MALFORMED, PI_ERROR, "packet too short")
        -- the correct way now:
        tree:add_proto_expert_info(ef_too_short)
        dprint("packet length",pktlen,"too short")
        return
    end

    -- Now let's add our transaction id under our dns protocol tree we just created.
    -- The transaction id starts at offset 0, for 2 bytes length.
    tree:add(pf_fh, tvbuf:range(0,1))
    tree:add(pf_rs485f, tvbuf:range(1,1))
    local rs485 = bit32.band(tvbuf:range(1,1):uint(), 0x20)
    tree:add(pf_af, tvbuf:range(1,1))
    local af = PASIVE
    if bit32.band(tvbuf:range(1,1):uint(), 0x10) > 0 then af = ACTIVE end
    tree:add(pf_mt, tvbuf:range(1,1))
    local mt = bit32.band(tvbuf:range(1,1):uint(), 0x0F)
    local mid = tvbuf:range(2,1):uint()
    if mt == 1 then
      tree:add(pf_mid_1, tvbuf:range(2,1))
      pktinfo.cols.info = tostring(pktinfo.cols.info) .. tMessagesIds[mt][mid]
    elseif mt == 2 then
      tree:add(pf_mid_2, tvbuf:range(2,1))
      pktinfo.cols.info = tostring(pktinfo.cols.info) .. tMessagesIds[mt][mid]
    elseif mt == 4 then
      tree:add(pf_mid_4, tvbuf:range(2,1))
      pktinfo.cols.info = tostring(pktinfo.cols.info) .. tMessagesIds[mt][mid]
    elseif mt == 5 then
      tree:add(pf_mid_5, tvbuf:range(2,1))
      pktinfo.cols.info = tostring(pktinfo.cols.info) .. tMessagesIds[mt][mid]
    else
      tree:add(pf_mid, tvbuf:range(2,1))
    end
    local data = 3
    if rs485 > 0 then
      tree:add(pf_sadr, tvbuf:range(3,1))
      data = 4
    end
    tree:add(pf_dlength, tvbuf:range(data, 2))
    local data_length = tvbuf:range(data,2):uint()

    data = data + 2
    if data_length > 0 then
		data_tree = tree:add(pf_data, tvbuf:range(data,data_length))
		if tParams[af] ~= nil and tParams[af][in_or_out] ~= nil and tParams[af][in_or_out][mt] ~= nil and tParams[af][in_or_out][mt][mid] ~= nil then
		  local params = tParams[af][in_or_out][mt][mid]
		  local ptr = data
		  local pid
		  local val
		  -- analise Mandatory
		  for k, v in ipairs(params) do
			if v[1] == 0 then --Mandatory
			  ptr = v[2](data_tree, tvbuf, ptr)
			end
		  end
		  local found = false
		  -- analise pids
		  while ptr < (data + data_length) do
			pid = tvbuf:range(ptr,1):uint()
			ptr = ptr + 1
			found = false
			for k, v in ipairs(params) do
			  if v[1] == pid then
				ptr = v[2](data_tree, tvbuf, ptr)
				found = true
				break
			  end
			end
			if not found then
			  data_tree:add(pf_string, tvbuf:range(ptr -1, 1), pid, "**pid not found: " .. pid)
			end
		  end
		else
		  tree:add(pf_string, tvbuf:range(data, data_length), "", string.format(" No params (AA%X%X%02X) [%x][%x][0x%x][0x%02x]",af,mt,mid, af, in_or_out, mt, mid))
		end

	  else
      tree:add(pf_data, tvbuf:range(data,data_length), "","--No data!")
      data_tree = tree
    end
    tree:add(pf_checksum, tvbuf:range(data + data_length, 2))
    --- analize data here!
    dprint2("clou.dissector returning",pktlen)

    -- tell wireshark how much of tvbuff we dissected
    return pktlen
end
----------------------------------------
-- we want to have our protocol dissection invoked for a specific UDP port,
-- so get the udp dissector table and add our protocol to it
DissectorTable.get("tcp.port"):add(default_settings.port, clou)

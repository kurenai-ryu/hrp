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
----------------------------------------
print("hello world2")
-- do not modify this table
local debug_level = {
    DISABLED = 0,
    LEVEL_1  = 1,
    LEVEL_2  = 2
}
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
local clou = Proto("clou","Clou TCP Protocol")

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
    [0] = "REGION_GB1",
    [1] = "REGION_GB2",
    [2] = "REGION_GB3",
    [3] = "REGION_FCC",
    [4] = "REGION_ETSI",
    [5] = "REGION_JP",
    [6] = "REGION_TW",
    [7] = "REGION_ID",
    [8] = "REGION_RUS"
}

local eFREQ_JMP = {
    [0] = "SEQUEN_SWITCH",
    [1] = "AUTO_SWITCH" --test if its correct (official is 0 too)
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
    [0x08] = "Query ser ver/client mode parameter",
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

local tParams = {
  [0x02] = {
    [0x0b] = {
      {0x01, "EPC baseband speed", 1, {[0]="Tari=25us, FM0, LHF=40khz",[255] = "Auto"}},
      {0x02, "default Q value", 1, {} },
      {0x03, "Session", 1, {} },
      {0x04, "inventory Flag", 1, {[0]="use flag A", [1]="use flag B", [2]="Use both A & B"}}
    },
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


clou.fields = {
  pf_fh, pf_rs485f, pf_af, pf_mt, pf_mid, pf_mid_1, pf_mid_2, pf_mid_4, pf_mid_5, pf_sadr, pf_dlength, pf_data, pf_checksum
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
    tree:add(pf_mt, tvbuf:range(1,1))
    local mt = bit32.band(tvbuf:range(1,1):uint(), 0x0F)
    if mt == 1 then
      tree:add(pf_mid_1, tvbuf:range(2,1))
    elseif mt == 2 then
      tree:add(pf_mid_2, tvbuf:range(2,1))
    else
      tree:add(pf_mid, tvbuf:range(2,1))
    end

    local mid = tvbuf:range(2,1):uint()
    local data = 3
    if rs485 > 0 then
      tree:add(pf_sadr, tvbuf:range(3,1))
      data = 4
    end
    tree:add(pf_dlength, tvbuf:range(data, 2))
    local data_length = tvbuf:range(data,2):uint()
    data = data + 2
    data_tree = tree:add(pf_data, tvbuf:range(data,data_length))
    if tParams[mt] ~= nil and tParams[mt][mid] ~= nil then
      local params = tParams[mt][mid]
      local ptr = data
      local pid
      local val
      local found = false
      -- analise Mandatory
      for k, v in ipairs(params) do
        if v[1] == 0 then
            val = tvbuf:range(ptr,v[3]):uint()
            ptr = ptr + v[3]
            if v[4][val] ~= nil then
              data_tree:append_text("\n\t" .. v[2] .. " -> " .. v[4][val])
            else
              data_tree:append_text("\n\t" .. v[2] .. " = " .. val)
            end
        end
      end
      -- analise pids
      while ptr < (data + data_length) do
        pid = tvbuf:range(ptr,1):uint()
        ptr = ptr + 1
        found = false
        for k, v in ipairs(params) do
          if v[1] == pid then
            val = tvbuf:range(ptr,v[3]):uint()
            ptr = ptr + v[3]
            if v[4][val] ~= nil then
              data_tree:append_text("\n\t" .. v[2] .. " -> " .. v[4][val])
            else
              data_tree:append_text("\n\t" .. v[2] .. " = " .. val)
            end
            found = true
            break
          end
        end
        if not found then
          data_tree:append_text("\n\t*pid not found: " .. pid)
        end
      end
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

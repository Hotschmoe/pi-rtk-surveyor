#!/bin/bash
# Pi RTK Surveyor service management

case "$1" in
    start)
        sudo systemctl start pi-rtk-surveyor
        echo "Service started"
        ;;
    stop)
        sudo systemctl stop pi-rtk-surveyor
        echo "Service stopped"
        ;;
    restart)
        sudo systemctl restart pi-rtk-surveyor
        echo "Service restarted"
        ;;
    status)
        sudo systemctl status pi-rtk-surveyor
        ;;
    logs)
        sudo journalctl -u pi-rtk-surveyor -f
        ;;
    enable)
        sudo systemctl enable pi-rtk-surveyor
        echo "Service enabled for auto-start"
        ;;
    disable)
        sudo systemctl disable pi-rtk-surveyor
        echo "Service disabled from auto-start"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        exit 1
        ;;
esac

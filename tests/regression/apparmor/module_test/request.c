#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kmod.h>
#include <linux/printk.h>

static char *request = NULL;
module_param(request, charp, S_IRUGO);
MODULE_PARM_DESC(request, "Name of the module to be requested");

int init_module(void)
{
	int rc = 0;

	if (!request) {
		printk(KERN_ERR "apparmor request: name of the module "
		       "to be requested must be specified\n");
		rc = -EINVAL;
		goto out;
	}

	rc = request_module(request);
	if (rc != 0) {
		printk(KERN_ERR "apparmor request: error requesting "
		       "module %s: %d\n", request, rc);
		goto out;
	}

	printk(KERN_INFO "apparmor request: loaded module\n");
out:
	return rc;
}

void cleanup_module(void)
{
	printk(KERN_INFO "apparmor request: unloaded module\n");
}

MODULE_LICENSE("GPL");
